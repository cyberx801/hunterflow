"""Append-only audit logging (HF-FR-140, HF-SEC-012).

All writes go through this service; the API exposes a read-only view. Sensitive
values in before/after snapshots are redacted before persistence.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from ..db.models import AuditEvent
from .logging import get_correlation_id, get_logger
from .redaction import redact_any

log = get_logger("hunterflow.audit")


class AuditService:
    @staticmethod
    def record(
        db: Session,
        action: str,
        entity_type: str | None = None,
        entity_id: str | None = None,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
        actor_id: str | None = None,
        ip: str | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            before=redact_any(before) if before is not None else None,
            after=redact_any(after) if after is not None else None,
            correlation_id=get_correlation_id(),
            ip=ip,
        )
        db.add(event)
        db.flush()
        log.info("audit_event", action=action, entity_type=entity_type, entity_id=entity_id)
        return event
