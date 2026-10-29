"""Dramatiq broker setup and actor registry (ADR-003).

- Production/dev: Redis broker.
- Tests: StubBroker (synchronous execution, no Redis required).
- Cancellation: DB-flag polling + subprocess-group kill (ADR-010; implemented
  without dramatiq-abort - same semantics, fewer dependencies; recorded in
  docs/implementation-decisions.md).
"""

from __future__ import annotations

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.brokers.stub import StubBroker

from ..core.config import Settings

_broker: dramatiq.Broker | None = None


def setup_broker(settings: Settings, stub: bool = False) -> None:
    global _broker
    if stub:
        _broker = StubBroker()
        StubBroker.emit_after = False  # do not log stub emissions
        dramatiq.set_broker(_broker)
        _rebind_actors(_broker)
        return
    _broker = RedisBroker(url=settings.redis_url)
    dramatiq.set_broker(_broker)
    _rebind_actors(_broker)
    import logging

    logging.getLogger("dramatiq").setLevel(logging.WARNING)


def _rebind_actors(broker: dramatiq.Broker) -> None:
    """Actors capture their broker at declaration time; point them at the configured one."""
    try:
        from . import actors

        for actor in (actors.run_scan_actor, actors.run_import_actor):
            actor.broker = broker
            broker.declare_actor(actor)
    except Exception:  # during import cycles, actors will bind later
        pass


def get_broker() -> dramatiq.Broker | None:
    return _broker
