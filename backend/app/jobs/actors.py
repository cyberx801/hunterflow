"""Dramatiq actors: scan execution and HAR import (ADR-003)."""

from __future__ import annotations

import dramatiq

from ..core.config import get_settings
from ..db.base import build_engine, build_session_factory

_db_factory_fn = None


def set_db_factory(fn) -> None:
    """Inject a session factory (used by tests to bind the actor to the test DB)."""
    global _db_factory_fn
    _db_factory_fn = fn


def _db_factory():
    if _db_factory_fn is not None:
        return _db_factory_fn()
    settings = get_settings()
    engine = build_engine(settings)
    return build_session_factory(engine)


@dramatiq.actor(max_retries=0)
def run_scan_actor(job_id: str) -> None:
    from .pipeline import run_scan_job

    settings = get_settings()
    run_scan_job(_db_factory(), settings, job_id)


@dramatiq.actor(max_retries=0)
def run_import_actor(import_job_id: str) -> None:
    from ..services.traffic import run_har_import

    settings = get_settings()
    run_har_import(_db_factory(), settings, import_job_id)


def _drain_if_stub(actor) -> None:
    """When the broker is a StubBroker (tests), consume messages synchronously
    with a short-lived Worker so the actor completes before the caller returns."""
    from dramatiq.brokers.stub import StubBroker

    if isinstance(actor.broker, StubBroker):
        worker = dramatiq.Worker(actor.broker, worker_timeout=500)
        worker.start()
        try:
            actor.broker.join(actor.queue_name, timeout=120_000)  # ms
        finally:
            worker.stop()


def enqueue_scan(job_id: str) -> None:
    run_scan_actor.send(job_id)
    _drain_if_stub(run_scan_actor)


def enqueue_import(import_job_id: str) -> None:
    run_import_actor.send(import_job_id)
    _drain_if_stub(run_import_actor)
