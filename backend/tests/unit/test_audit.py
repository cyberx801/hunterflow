"""Audit service tests (T-005): append-only records, redaction of secrets."""

from __future__ import annotations

from app.core.audit import AuditService
from app.core.redaction import redact_text
from app.db.models import AuditEvent


def test_audit_record_persisted(db):
    AuditService.record(db, "test.action", "programs", "abc", {"a": 1}, {"b": 2})
    db.commit()
    rows = db.query(AuditEvent).all()
    assert len(rows) == 1
    assert rows[0].action == "test.action"
    assert rows[0].entity_id == "abc"


def test_audit_redacts_secrets(db):
    AuditService.record(
        db,
        "test.action",
        after={"headers": {"Authorization": "Bearer supersecrettoken"}},
    )
    db.commit()
    evt = db.query(AuditEvent).order_by(AuditEvent.created_at.desc()).first()
    assert "supersecrettoken" not in str(evt.after)
    assert "Authorization" in str(evt.after)


def test_redaction_patterns():
    cases = [
        "Authorization: Bearer abc.def.ghi",
        "Cookie: session=sekrit",
        "Set-Cookie: session=sekrit; Path=/",
        "AKIAIOSFODNN7EXAMPLE",
        '{"api_key": "long-secret-value-here"}',
    ]
    for text in cases:
        out = redact_text(text)
        assert "sekrit" not in out
        assert "abc.def.ghi" not in out
        assert "AKIAIOSFODNN7EXAMPLE" not in out
        assert "long-secret-value-here" not in out
