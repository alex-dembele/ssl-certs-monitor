"""Boucle de planification des vérifications SSL selon l'intervalle configuré."""

import asyncio
import os
import time
from datetime import datetime

try:
    from .cron_job import main as run_checks
    from .database import SessionLocal
    from .settings import GLOBAL_SCOPE, NotificationSettings
except ImportError:
    from cron_job import main as run_checks
    from database import SessionLocal
    from settings import GLOBAL_SCOPE, NotificationSettings

DEFAULT_INTERVAL_MINUTES = 60
# Fréquence de relecture du paramètre pendant l'attente : un intervalle
# raccourci depuis l'UI s'applique sans attendre la fin du précédent.
SETTINGS_POLL_SECONDS = 60


def check_interval_minutes() -> int:
    """Intervalle des paramètres globaux, sinon CHECK_INTERVAL_MINUTES, sinon 60."""
    try:
        with SessionLocal() as session:
            settings = session.get(NotificationSettings, GLOBAL_SCOPE)
            if settings is not None:
                return max(1, settings.check_interval_minutes)
    except Exception as error:
        print(f"-> Paramètres illisibles ({error}), intervalle par défaut utilisé.")
    return max(1, int(os.getenv("CHECK_INTERVAL_MINUTES", DEFAULT_INTERVAL_MINUTES)))


def wait_for_next_run(started: float) -> None:
    while True:
        remaining = check_interval_minutes() * 60 - (time.monotonic() - started)
        if remaining <= 0:
            return
        time.sleep(min(remaining, SETTINGS_POLL_SECONDS))


def run_forever(max_runs: int | None = None) -> None:
    runs = 0
    while max_runs is None or runs < max_runs:
        started = time.monotonic()
        try:
            asyncio.run(run_checks())
        except Exception as error:
            print(f"-> Échec de la vérification planifiée ({datetime.now()}): {error}")
        runs += 1
        print(f"-> Prochaine vérification dans {check_interval_minutes()} minute(s).")
        wait_for_next_run(started)


if __name__ == "__main__":
    run_forever()
