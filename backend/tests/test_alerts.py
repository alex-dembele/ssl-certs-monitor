from datetime import datetime, timedelta

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from backend.alerts import AlertState, NotificationLog, record_notification, select_alert_events
from backend.database import Base, Domain


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
