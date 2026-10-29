"""Program and scope services: policy versioning, rule lifecycle."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.audit import AuditService
from ..core.errors import ApiError, ErrorCode
from ..db.models import PolicyVersion, Program, ScopeRule
from ..domain.scope import Policy, Rule

VALID_PLATFORMS = {"hackerone", "bugcrowd", "intigriti", "other"}


def get_program(db: Session, program_id: str) -> Program:
    program = db.get(Program, program_id)
    if program is None:
        raise ApiError(ErrorCode.NOT_FOUND, "Program not found", 404)
    return program


def current_policy(db: Session, program: Program) -> Policy:
    rules = db.scalars(
        select(ScopeRule)
        .where(ScopeRule.program_id == program.id, ScopeRule.policy_version_id.is_(None))
        .order_by(ScopeRule.priority)
    ).all()
    return Policy.from_db_rules(rules)


def latest_policy_version(db: Session, program_id: str) -> int:
    rows = db.scalars(
        select(PolicyVersion)
        .where(PolicyVersion.program_id == program_id)
        .order_by(PolicyVersion.version.desc())
        .limit(1)
    ).all()
    return rows[0].version if rows else 0


def publish_policy_version(
    db: Session,
    program: Program,
    change_summary: str,
    actor_id: str | None = None,
    ip: str | None = None,
) -> PolicyVersion:
    """Snapshot the current rules into an immutable version and bump the counter."""
    rules = db.scalars(
        select(ScopeRule).where(ScopeRule.program_id == program.id).order_by(ScopeRule.priority)
    ).all()
    if not rules:
        raise ApiError(ErrorCode.BAD_STATE, "Cannot publish an empty policy; add at least one rule")
    version_no = latest_policy_version(db, program.id) + 1
    snapshot = Policy.from_db_rules(rules).to_snapshot()
    pv = PolicyVersion(
        program_id=program.id,
        version=version_no,
        change_summary=change_summary,
        snapshot=snapshot,
    )
    db.add(pv)
    db.flush()
    AuditService.record(
        db,
        "policy.published",
        "policy_version",
        pv.id,
        after={"version": version_no, "rules": snapshot},
        actor_id=actor_id,
        ip=ip,
    )
    return pv


def policy_at_version(db: Session, program_id: str, version: int) -> Policy:
    pv = db.scalar(
        select(PolicyVersion).where(
            PolicyVersion.program_id == program_id, PolicyVersion.version == version
        )
    )
    if pv is None:
        raise ApiError(ErrorCode.NOT_FOUND, "Policy version not found", 404)
    return Policy.from_snapshot(pv.snapshot)


def validate_rule_value(kind: str, value: str) -> None:
    """Basic sanity validation of rule values (never a security boundary -
    the engine's semantics are; this prevents obvious garbage)."""
    import ipaddress
    import re

    if kind in ("domain_exact", "domain_wildcard"):
        v = value.lower().rstrip(".")
        if kind == "domain_wildcard":
            if not v.startswith("*.") or len(v) <= 2:
                raise ApiError(ErrorCode.VALIDATION, "Wildcard must look like *.example.com")
            v = v[2:]
        if not re.fullmatch(r"[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+", v):
            raise ApiError(ErrorCode.VALIDATION, f"Invalid domain: {value}")
    elif kind == "cidr":
        try:
            ipaddress.ip_network(value, strict=False)
        except ValueError:
            raise ApiError(ErrorCode.VALIDATION, f"Invalid CIDR: {value}") from None
    elif kind == "url_path":
        if not value.startswith("/"):
            raise ApiError(ErrorCode.VALIDATION, "Path rules must start with /")
    elif kind == "method":
        if value.upper() not in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}:
            raise ApiError(ErrorCode.VALIDATION, f"Invalid method: {value}")
    elif kind == "automation":
        if value.lower() not in {"allowed", "denied", "confirm"}:
            raise ApiError(ErrorCode.VALIDATION, "automation must be allowed|denied|confirm")
    elif kind == "rate_limit":
        if not value.replace(".", "", 1).isdigit():
            raise ApiError(ErrorCode.VALIDATION, "rate_limit must be a number (requests/second)")


def to_rule(row: ScopeRule) -> Rule:
    return Rule(
        kind=row.kind,
        value=row.value,
        effect=row.effect,
        priority=row.priority,
        note=row.notes,
    )
