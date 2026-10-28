import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base, add_domains, delete_domain, list_domains, list_statuses, save_statuses


def test_concurrent_safe_upserts_and_status_persistence(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'monitor.db'}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)

    with sessions() as session:
        assert add_domains(session, ["example.com", "example.net"]) == ["example.com", "example.net"]
    with sessions() as session:
        assert add_domains(session, ["example.com", "example.org"]) == ["example.org"]

    with sessions() as session:
        save_statuses(
            session,
            [{"domain": "example.com", "status": "OK", "days_left": 90, "expiry_date": "2027-01-01T00:00:00"}],
        )

    with sessions() as session:
        assert list_domains(session) == ["example.com", "example.net", "example.org"]
        assert list_statuses(session)[0]["days_left"] == 90
        assert delete_domain(session, "example.net") is True
        assert delete_domain(session, "missing.example") is False


def test_legacy_migration_input_is_readable(tmp_path):
    legacy = tmp_path / "domains.json"
    legacy.write_text(json.dumps(["example.com"]))
    assert json.loads(legacy.read_text()) == ["example.com"]
