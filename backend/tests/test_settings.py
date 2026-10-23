import json

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from backend.settings import SettingsAuditLog, get_settings, settings_to_dict
from backend.database import Base


def test_personal_and_organization_settings_are_separate(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'settings.db'}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)

    with sessions() as session:
        personal = get_settings(session, "personal")
        organization = get_settings(session, "organization")
        personal.threshold_days = 14
        personal.recipients = json.dumps(["owner@example.com"])
        session.add_all([personal, organization, SettingsAuditLog(scope="personal", changed_fields='["threshold_days"]')])
        session.commit()

        assert settings_to_dict(session.get(type(personal), "personal"))["threshold_days"] == 14
        assert settings_to_dict(session.get(type(organization), "organization"))["threshold_days"] == 30
        assert session.scalar(select(SettingsAuditLog.scope)) == "personal"
