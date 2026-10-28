import asyncio
import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import backend.cron_job as cron_job
from backend.database import Base, Domain
from backend.notifications import DeliveryResult
from backend.settings import GLOBAL_SCOPE, NotificationSettings


def test_scheduled_run_delivers_to_global_recipients(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'cron.db'}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    with sessions() as session:
        session.add_all([
            Domain(name="example.com"),
            NotificationSettings(scope=GLOBAL_SCOPE, recipients=json.dumps(["ops@example.com"])),
        ])
        session.commit()

    async def expiring(domain):
        return {"domain": domain, "status": "Expire bientôt", "days_left": 5, "checked_at": "2026-01-01T00:00:00"}

    delivered = {}

    def capture(events, email_recipients=None):
        delivered["recipients"] = email_recipients
        return [DeliveryResult(event, True, "delivered", 1, "k" * 64) for event in events]

    monkeypatch.setattr(cron_job, "SessionLocal", sessions)
    monkeypatch.setattr(cron_job, "initialize_database", lambda: None)
    monkeypatch.setattr(cron_job, "get_ssl_expiry_info", expiring)
    monkeypatch.setattr(cron_job, "deliver_events", capture)

    asyncio.run(cron_job.main())

    assert delivered["recipients"] == ["ops@example.com"]
