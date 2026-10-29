"""Findings API: lifecycle, verification honesty, duplicates (HF-FR-080..084).

Constitution P4/P5: only humans verify findings; scanner imports remain
`potential`/`unverified`; duplicate linking preserves provenance.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import or_, select

from ...core.audit import AuditService
from ...core.errors import ApiError, ErrorCode
from ...db.models import Finding, FindingLink, FindingStatusHistory, User
from ...domain.dedup import duplicate_score
from ...domain.state import FINDING_TRANSITIONS, TransitionError, assert_transition
from ...schemas.findings import (
    FindingCreate,
    FindingLinkCreate,
    FindingOut,
    FindingTransition,
    FindingUpdate,
)
from ..deps import get_current_user, get_db, parse_uuid, require_csrf
from ._common import ListParams, Page, paginate

router = APIRouter(tags=["findings"])


def _out(f: Finding) -> FindingOut:
    return FindingOut(
        id=f.id,
        program_id=f.program_id,
        title=f.title,
        description=f.description,
        category=f.category,
        cwe=f.cwe,
        asset_id=f.asset_id,
        endpoint_id=f.endpoint_id,
        severity=f.severity,
        confidence=f.confidence,
        impact=f.impact,
        reproduction_steps=f.reproduction_steps,
        status=f.status,
        validation_status=f.validation_status,
        discovery_source=f.discovery_source,
        source_ref=f.source_ref,
        created_at=f.created_at,
        updated_at=f.updated_at,
    )


def _get(db, finding_id: str) -> Finding:
    finding = db.get(Finding, parse_uuid(finding_id))
    if finding is None:
        raise ApiError(ErrorCode.NOT_FOUND, "Finding not found", 404)
    return finding


@router.get("/findings")
def list_findings(
    params: ListParams = Depends(),
    program_id: str | None = None,
    status: str | None = None,
    severity: str | None = None,
    unverified_only: bool = False,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
) -> Page[FindingOut]:
    stmt = select(Finding)
    if program_id:
        stmt = stmt.where(Finding.program_id == parse_uuid(program_id))
    if status:
        stmt = stmt.where(Finding.status == status)
    if severity:
        stmt = stmt.where(Finding.severity == severity)
    if unverified_only:
        stmt = stmt.where(Finding.validation_status == "unverified")
    if params.q:
        like = f"%{params.q}%"
        stmt = stmt.where(or_(Finding.title.ilike(like), Finding.description.ilike(like)))
    rows, total = paginate(db, stmt, params.page, params.page_size, Finding.updated_at.desc())
    return Page(items=[_out(f) for f in rows], total=total, page=params.page, page_size=params.page_size)


@router.post("/findings")
def create_finding(
    body: FindingCreate,
    request: Request,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> FindingOut:
    finding = Finding(
        program_id=parse_uuid(body.program_id),
        title=body.title,
        description=body.description,
        category=body.category,
        cwe=body.cwe,
        asset_id=body.asset_id,
        endpoint_id=body.endpoint_id,
        severity=body.severity,
        confidence=body.confidence,
        impact=body.impact,
        reproduction_steps=body.reproduction_steps,
        discovery_source=body.discovery_source,
        source_ref=body.source_ref,
        status="potential",
        validation_status="unverified",
    )
    db.add(finding)
    db.flush()
    AuditService.record(db, "finding.created", "finding", finding.id, after={"title": finding.title}, actor_id=user.id)
    db.commit()
    return _out(finding)


@router.get("/findings/{finding_id}")
def get_finding(finding_id: str, db=Depends(get_db), user: User = Depends(get_current_user)) -> FindingOut:
    return _out(_get(db, finding_id))


@router.patch("/findings/{finding_id}")
def update_finding(
    finding_id: str,
    body: FindingUpdate,
    request: Request,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> FindingOut:
    finding = _get(db, finding_id)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(finding, key, value)
    db.commit()
    return _out(finding)


@router.post("/findings/{finding_id}/transition")
def transition_finding(
    finding_id: str,
    body: FindingTransition,
    request: Request,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> FindingOut:
    finding = _get(db, finding_id)
    try:
        assert_transition(FINDING_TRANSITIONS, finding.status, body.to)
    except TransitionError:
        raise ApiError(
            ErrorCode.BAD_STATE, f"Invalid transition: {finding.status} -> {body.to}"
        ) from None
    if body.to == "verified":
        # Constitution P4: only an explicit human confirmation verifies a finding.
        if not body.verified_human_confirmation:
            raise ApiError(
                ErrorCode.FORBIDDEN,
                "Marking a finding verified requires explicit human confirmation",
                403,
            )
        finding.validation_status = "verified_human"
    db.add(
        FindingStatusHistory(
            finding_id=finding.id, from_status=finding.status, to_status=body.to,
            changed_by=user.id,
        )
    )
    finding.status = body.to
    AuditService.record(
        db, "finding.transition", "finding", finding.id,
        before={"status": finding.status}, after={"status": body.to}, actor_id=user.id,
    )
    db.commit()
    return _out(finding)


@router.get("/findings/{finding_id}/duplicates")
def find_duplicates(
    finding_id: str, db=Depends(get_db), user: User = Depends(get_current_user)
) -> list[dict]:
    finding = _get(db, finding_id)
    endpoint = None
    if finding.endpoint_id:
        from ...db.models import Endpoint

        ep = db.get(Endpoint, finding.endpoint_id)
        if ep is not None:
            endpoint = f"{ep.method} {ep.path}"
    candidates = db.scalars(
        select(Finding).where(Finding.program_id == finding.program_id, Finding.id != finding.id)
    ).all()
    out = []
    for other in candidates:
        other_endpoint = None
        if other.endpoint_id:
            from ...db.models import Endpoint

            ep2 = db.get(Endpoint, other.endpoint_id)
            if ep2 is not None:
                other_endpoint = f"{ep2.method} {ep2.path}"
        result = duplicate_score(
            endpoint, other_endpoint, finding.category, other.category,
            finding.title, other.title,
        )
        if result.score >= 0.35:
            out.append(
                {
                    "finding_id": other.id,
                    "title": other.title,
                    "score": result.score,
                    "reasons": result.reasons,
                    "status": other.status,
                }
            )
    out.sort(key=lambda x: x["score"], reverse=True)
    return out


@router.post("/findings/{finding_id}/links")
def link_finding(
    finding_id: str,
    body: FindingLinkCreate,
    request: Request,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> dict:
    finding = _get(db, finding_id)
    other = db.get(Finding, parse_uuid(body.linked_finding_id))
    if other is None or other.program_id != finding.program_id:
        raise ApiError(ErrorCode.NOT_FOUND, "Linked finding not found", 404)
    link = FindingLink(
        finding_id=finding.id, linked_finding_id=other.id, kind=body.kind, note=body.note
    )
    db.add(link)
    if body.kind == "duplicate_of":
        if finding.status not in ("duplicate", "resolved", "false_positive"):
            finding.status = "duplicate"
    db.commit()
    return {"status": "ok", "link_id": link.id}


@router.get("/findings/{finding_id}/links")
def list_links(
    finding_id: str, db=Depends(get_db), user: User = Depends(get_current_user)
) -> list[dict]:
    finding = _get(db, finding_id)
    rows = db.scalars(
        select(FindingLink).where(FindingLink.finding_id == finding.id)
    ).all()
    return [
        {"id": l.id, "linked_finding_id": l.linked_finding_id, "kind": l.kind, "note": l.note}
        for l in rows
    ]
