from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import backend.scheduler as scheduler
from backend.database import Base
from backend.settings import GLOBAL_SCOPE, NotificationSettings


def _sessions(tmp_path, monkeypatch, interval=None):
    engine = create_engine(f"sqlite:///{tmp_path / 'scheduler.db'}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    if interval is not None:
        with sessions() as session:
            session.add(NotificationSettings(scope=GLOBAL_SCOPE, check_interval_minutes=interval))
            session.commit()
    monkeypatch.setattr(scheduler, "SessionLocal", sessions)
    return sessions


def test_interval_comes_from_global_settings(tmp_path, monkeypatch):
    _sessions(tmp_path, monkeypatch, interval=15)
    monkeypatch.setenv("CHECK_INTERVAL_MINUTES", "120")

    assert scheduler.check_interval_minutes() == 15


def test_interval_falls_back_to_environment_then_default(tmp_path, monkeypatch):
    _sessions(tmp_path, monkeypatch)
    monkeypatch.setenv("CHECK_INTERVAL_MINUTES", "120")
    assert scheduler.check_interval_minutes() == 120

    monkeypatch.delenv("CHECK_INTERVAL_MINUTES")
    assert scheduler.check_interval_minutes() == scheduler.DEFAULT_INTERVAL_MINUTES


def test_scheduler_waits_for_the_configured_interval(tmp_path, monkeypatch):
    _sessions(tmp_path, monkeypatch, interval=2)
    clock = {"now": 0.0}
    runs = []

    async def fake_checks():
        runs.append(clock["now"])
        clock["now"] += 10

    def fake_sleep(seconds):
        clock["now"] += seconds

    monkeypatch.setattr(scheduler, "run_checks", fake_checks)
    monkeypatch.setattr(scheduler.time, "monotonic", lambda: clock["now"])
    monkeypatch.setattr(scheduler.time, "sleep", fake_sleep)

    scheduler.run_forever(max_runs=2)

    assert runs == [0.0, 120.0]


def test_failed_run_does_not_stop_the_scheduler(tmp_path, monkeypatch):
    _sessions(tmp_path, monkeypatch, interval=1)
    calls = []

    async def failing_checks():
        calls.append(1)
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(scheduler, "run_checks", failing_checks)
    monkeypatch.setattr(scheduler, "wait_for_next_run", lambda _started: None)

    scheduler.run_forever(max_runs=2)

    assert len(calls) == 2
