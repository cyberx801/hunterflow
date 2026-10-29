"""Scheduler process: polls due scheduled scans and enqueues them.

Run as its own container/process (`python -m app.jobs.scheduler`). Single
instance is assumed; the DB is the source of truth for next_run_at. See
docs/server-deployment.md.
"""

from __future__ import annotations

import time

from ..core.config import get_settings
from ..core.logging import configure_logging, get_logger
from ..db.base import build_engine, build_session_factory
from .broker import setup_broker

log = get_logger("hunterflow.scheduler")


def main() -> None:
    settings = get_settings()
    configure_logging(settings)
    setup_broker(settings, stub=False)
    engine = build_engine(settings)
    factory = build_session_factory(engine)

    log.info("scheduler_started", interval_seconds=settings.scheduler_interval_seconds)
    try:
        while True:
            db = factory()
            try:
                from ..services.monitoring import run_due_schedules

                count = run_due_schedules(db, settings)
                if count:
                    log.info("schedules_enqueued", count=count)
            except Exception:
                log.exception("scheduler_tick_failed")
            finally:
                db.close()
            time.sleep(settings.scheduler_interval_seconds)
    except KeyboardInterrupt:
        log.info("scheduler_stopped")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
