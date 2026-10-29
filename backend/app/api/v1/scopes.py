"""Scope API: rules CRUD, policy versions, preview, confirmation (HF-FR-005..009)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select

from ...core.audit import AuditService
from ...core.errors import ApiError, ErrorCode
from ...db.models import Asset, PolicyVersion, Program, ScopeRule, User
from ...domain.scope import Policy
from ...schemas.programs import (
    PolicyVersionDetail,
    PolicyVersionOut,
    ScopePreviewRequest,
    ScopePreviewResult,
    ScopeRuleCreate,
    ScopeRuleOut,
)
from ...services import programs as programs_service
from ..deps import get_current_user, get_db, parse_uuid, require_csrf

router = APIRouter(tags=["scope"])


def _rule_out(rule: ScopeRule) -> ScopeRuleOut:
    return ScopeRuleOut(
        id=rule.id, kind=rule.kind, value=rule.value, effect=rule.effect,
        priority=rule.priority, notes=rule.notes,
    )


@router.get("/programs/{program_id}/scope")
def list_rules(
    program_id: str, db=Depends(get_db), user: User = Depends(get_current_user)
) -> list[ScopeRuleOut]:
    program = programs_service.get_program(db, parse_uuid(program_id))
    rules = db.scalars(
        select(ScopeRule).where(ScopeRule.program_id == program.id).order_by(ScopeRule.priority)
    ).all()
    return [_rule_out(r) for r in rules]


@router.post("/programs/{program_id}/scope/rules")
def add_rule(
    program_id: str,
    body: ScopeRuleCreate,
    request: Request,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> ScopeRuleOut:
    program = programs_service.get_program(db, parse_uuid(program_id))
    programs_service.validate_rule_value(body.kind.value, body.value)
    rule = ScopeRule(
        program_id=program.id,
        kind=body.kind.value,
        value=body.value.strip(),
        effect=body.effect.value,
        priority=body.priority,
        notes=body.notes,
    )
    db.add(rule)
    db.flush()
    AuditService.record(
        db, "scope.rule_added", "scope_rule", rule.id,
        after={"kind": rule.kind, "value": rule.value, "effect": rule.effect},
        actor_id=user.id, ip=request.client.host if request.client else None,
    )
    db.commit()
    return _rule_out(rule)


@router.patch("/programs/{program_id}/scope/rules/{rule_id}")
def update_rule(
    program_id: str,
    rule_id: str,
    body: ScopeRuleCreate,
    request: Request,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> ScopeRuleOut:
    program = programs_service.get_program(db, parse_uuid(program_id))
    rule = db.get(ScopeRule, parse_uuid(rule_id))
    if rule is None or rule.program_id != program.id:
        raise ApiError(ErrorCode.NOT_FOUND, "Rule not found", 404)
    programs_service.validate_rule_value(body.kind.value, body.value)
    rule.kind = body.kind.value
    rule.value = body.value.strip()
    rule.effect = body.effect.value
    rule.priority = body.priority
    rule.notes = body.notes
    AuditService.record(
        db, "scope.rule_updated", "scope_rule", rule.id,
        after={"kind": rule.kind, "value": rule.value, "effect": rule.effect},
        actor_id=user.id, ip=request.client.host if request.client else None,
    )
    db.commit()
    return _rule_out(rule)


@router.delete("/programs/{program_id}/scope/rules/{rule_id}")
def delete_rule(
    program_id: str,
    rule_id: str,
    request: Request,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> dict:
    program = programs_service.get_program(db, parse_uuid(program_id))
    rule = db.get(ScopeRule, parse_uuid(rule_id))
    if rule is None or rule.program_id != program.id:
        raise ApiError(ErrorCode.NOT_FOUND, "Rule not found", 404)
    db.delete(rule)
    AuditService.record(
        db, "scope.rule_deleted", "scope_rule", rule.id,
        before={"kind": rule.kind, "value": rule.value},
        actor_id=user.id, ip=request.client.host if request.client else None,
    )
    db.commit()
    return {"status": "ok"}


@router.post("/programs/{program_id}/scope/preview")
def preview(
    program_id: str,
    body: ScopePreviewRequest,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ScopePreviewResult]:
    program = programs_service.get_program(db, parse_uuid(program_id))
    policy = programs_service.current_policy(db, program)
    results = []
    for target in body.targets:
        decision = policy.evaluate_url(target, method=body.methods[0])
        results.append(
            ScopePreviewResult(
                target=target,
                allowed=decision.allowed,
                requires_confirmation=decision.requires_confirmation,
                matched_rules=[r.describe() for r in decision.matched_rules],
                reason=decision.reason,
            )
        )
    return results


@router.post("/programs/{program_id}/scope/versions")
def publish_version(
    program_id: str,
    request: Request,
    body: dict | None = None,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> PolicyVersionOut:
    program = programs_service.get_program(db, parse_uuid(program_id))
    pv = programs_service.publish_policy_version(
        db, program, (body or {}).get("change_summary") or "",
        actor_id=user.id, ip=request.client.host if request.client else None,
    )
    db.commit()
    return PolicyVersionOut(
        id=pv.id, version=pv.version, change_summary=pv.change_summary,
        created_at=pv.created_at, rule_count=len(pv.snapshot.get("rules", [])),
    )


@router.get("/programs/{program_id}/scope/versions")
def list_versions(
    program_id: str, db=Depends(get_db), user: User = Depends(get_current_user)
) -> list[PolicyVersionOut]:
    program = programs_service.get_program(db, parse_uuid(program_id))
    rows = db.scalars(
        select(PolicyVersion)
        .where(PolicyVersion.program_id == program.id)
        .order_by(PolicyVersion.version.desc())
    ).all()
    return [
        PolicyVersionOut(
            id=pv.id, version=pv.version, change_summary=pv.change_summary,
            created_at=pv.created_at, rule_count=len(pv.snapshot.get("rules", [])),
        )
        for pv in rows
    ]


@router.get("/programs/{program_id}/scope/versions/{version}")
def get_version(
    program_id: str,
    version: int,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
) -> PolicyVersionDetail:
    program = programs_service.get_program(db, parse_uuid(program_id))
    pv = db.scalar(
        select(PolicyVersion).where(
            PolicyVersion.program_id == program.id, PolicyVersion.version == version
        )
    )
    if pv is None:
        raise ApiError(ErrorCode.NOT_FOUND, "Policy version not found", 404)
    prev = db.scalar(
        select(PolicyVersion)
        .where(PolicyVersion.program_id == program.id, PolicyVersion.version == version - 1)
    )
    return PolicyVersionDetail(
        id=pv.id, version=pv.version, change_summary=pv.change_summary,
        created_at=pv.created_at, rule_count=len(pv.snapshot.get("rules", [])),
        rules=[ScopeRuleOut(id="", kind=r["kind"], value=r["value"], effect=r["effect"], priority=r["priority"], notes=r.get("note")) for r in pv.snapshot.get("rules", [])],
        previous_rules=(
            [ScopeRuleOut(id="", kind=r["kind"], value=r["value"], effect=r["effect"], priority=r["priority"], notes=r.get("note")) for r in prev.snapshot.get("rules", [])]
            if prev else None
        ),
    )
