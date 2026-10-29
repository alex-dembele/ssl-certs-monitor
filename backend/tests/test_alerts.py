from datetime import datetime, timedelta

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from backend.alerts import AlertState, NotificationLog, record_notification, select_alert_events
from backend.database import Base, Domain
from backend.notifications import idempotency_key
from backend.settings import GLOBAL_SCOPE, NotificationSettings


def test_alerts_are_deduplicated_reminded_and_resolved(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'alerts.db'}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    now = datetime(2026, 1, 1)
    critical = {"domain": "example.com", "status": "Expire bientôt", "days_left": 10}
    healthy = {"domain": "example.com", "status": "OK", "days_left": 90}

    with sessions() as session:
        session.add(Domain(name="example.com"))
        session.commit()
        first = select_alert_events(session, [critical], now)
        assert [event.event_type for event in first] == ["problem"]
        record_notification(session, first, True, now=now)

        assert select_alert_events(session, [critical], now + timedelta(days=1)) == []
        reminder = select_alert_events(session, [critical], now + timedelta(days=8))
        assert [event.event_type for event in reminder] == ["reminder"]
        record_notification(session, reminder, True, now=now + timedelta(days=8))

        resolution = select_alert_events(session, [healthy], now + timedelta(days=8))
        assert [event.event_type for event in resolution] == ["resolved"]
        record_notification(session, resolution, True, now=now + timedelta(days=8))

        assert session.scalar(select(AlertState.state).where(AlertState.domain_name == "example.com")) == "healthy"
        assert session.scalar(select(NotificationLog.success).where(NotificationLog.domain_name == "example.com")) is True


def test_successive_reminders_keep_distinct_delivery_records(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'reminders.db'}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    now = datetime(2026, 1, 1)
    critical = {"domain": "example.com", "status": "Expire bientôt", "days_left": 10, "fingerprint": "abc"}

    with sessions() as session:
        session.add(Domain(name="example.com"))
        session.commit()
        record_notification(session, select_alert_events(session, [critical], now), True, now=now)
        keys = []
        for week in (1, 2):
            when = now + timedelta(days=7 * week)
            reminders = select_alert_events(session, [critical], when)
            assert [event.event_type for event in reminders] == ["reminder"]
            keys.append(idempotency_key(reminders[0]))
            record_notification(session, reminders, True, now=when, idempotency_key=keys[-1])

        assert keys[0] != keys[1]
        logged = session.scalars(select(NotificationLog.event_type).where(NotificationLog.event_type == "reminder")).all()
        assert len(logged) == 2


def test_global_settings_drive_domains_without_policy(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'global.db'}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    now = datetime(2026, 1, 1)
    certificate = {"domain": "example.com", "status": "OK", "days_left": 20}

    with sessions() as session:
        session.add_all([Domain(name="example.com"), NotificationSettings(scope=GLOBAL_SCOPE, threshold_days=14, channel="slack")])
        session.commit()
        assert select_alert_events(session, [certificate], now) == []

        session.get(NotificationSettings, GLOBAL_SCOPE).threshold_days = 30
        events = select_alert_events(session, [certificate], now)
        assert [(event.event_type, event.channel) for event in events] == [("problem", "slack")]

        session.get(NotificationSettings, GLOBAL_SCOPE).enabled = False
        assert select_alert_events(session, [certificate], now) == []
