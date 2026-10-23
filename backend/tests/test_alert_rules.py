import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.alerts import AlertRule, DomainContext, select_alert_events
from backend.database import Base, Domain


def test_rule_resolution_prefers_priority_then_explains_match(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'rules.db'}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)

    with sessions() as session:
        session.add_all([
            Domain(name="api.example.com"),
            DomainContext(domain_name="api.example.com", team="platform", project="core", environment="production", criticality="high"),
            AlertRule(name="team default", scope_type="team", scope_key="platform", owner_team="platform", priority=10, threshold_days=30, conditions="{}", channels='["email"]'),
            AlertRule(name="production override", scope_type="environment", scope_key="production", owner_team="platform", priority=20, threshold_days=60, conditions=json.dumps({"criticalities": ["high"]}), channels='["webhook"]'),
        ])
        session.commit()

        events = select_alert_events(session, [{"domain": "api.example.com", "status": "OK", "days_left": 45}])

        assert len(events) == 1
        assert events[0].rule_name == "production override"
        assert events[0].channel == "webhook"
        assert "production override" in events[0].explanation
