"""Dramatiq broker setup and actor registry (ADR-003).

- Production/dev: Redis broker.
- Tests: StubBroker (synchronous execution, no Redis required).
- Cancellation: DB-flag polling + subprocess-group kill (ADR-010; implemented
  without dramatiq-abort - same semantics, fewer dependencies; recorded in
  docs/implementation-decisions.md).
"""

from __future__ import annotations

import dramatiq
from dramatiq.brokers.stub import StubBroker
from dramatiq.brokers.redis import RedisBroker

from ..core.config import Settings

_broker: dramatiq.Broker | None = None


def setup_broker(settings: Settings, stub: bool = False) -> None:
    global _broker
    if stub:
        _broker = StubBroker()
        StubBroker.emit_after = False  # do not log stub emissions
        dramatiq.set_broker(_broker)
        return
    _broker = RedisBroker(url=settings.redis_url)
    dramatiq.set_broker(_broker)
    import logging

    logging.getLogger("dramatiq").setLevel(logging.WARNING)


def get_broker() -> dramatiq.Broker | None:
    return _broker
