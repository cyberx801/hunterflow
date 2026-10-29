"""Overview + settings + audit API (HF-FR-130/140/170)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from ...core.config import Settings, get_settings
from ...db.models import (
    Asset,
    AuditEvent,
    Endpoint,
    Finding,
    Program,
    ResearchCard,
    ScanJob,
    Setting,
    Tool,
    User,
)
from ...schemas.findings import OverviewOut, SettingsUpdate, ToolOut
from ...services.tools import detect_all
from ..deps import get_current_user, get_db, require_csrf

router = APIRouter(tags=["platform"])


@router.get("/overview")
def overview(db=Depends(get_db), user: User = Depends(get_current_user)) -> OverviewOut:
    program_count = db.scalar(select(func.count()).select_from(Program).where(Program.archived_at.is_(None))) or 0
    asset_count = db.scalar(select(func.count()).select_from(Asset)) or 0
    endpoint_count = db.scalar(select(func.count()).select_from(Endpoint)) or 0
    finding_count = db.scalar(select(func.count()).select_from(Finding)) or 0
    unverified = db.scalar(
        select(func.count()).select_from(Finding).where(
            Finding.validation_status == "unverified",
            Finding.status.in_(["potential", "under_investigation"]),
        )
    ) or 0
    active_scans = db.scalar(
        select(func.count()).select_from(ScanJob).where(
            ScanJob.status.in_(["queued", "running"])
        )
    ) or 0

    queue_cards = db.scalars(
        select(ResearchCard)
        .where(ResearchCard.status.in_(["in_progress", "needs_verification", "not_started"]))
        .order_by(ResearchCard.priority_score.desc())
        .limit(5)
    ).all()
    research_queue = [
        {
            "id": c.id,
            "title": c.title,
            "status": c.status,
            "priority_score": c.priority_score,
            "factors": c.priority_factors,
        }
        for c in queue_cards
    ]

    need_verification = db.scalars(
        select(Finding)
        .where(
            Finding.validation_status == "unverified",
            Finding.status.in_(["potential", "under_investigation"]),
        )
        .order_by(Finding.updated_at.desc())
        .limit(5)
    ).all()
    findings_needing_verification = [
        {"id": f.id, "title": f.title, "severity": f.severity, "status": f.status} for f in need_verification
    ]

    since = datetime.now(timezone.utc) - timedelta(days=1)
    recent_assets = db.scalars(
        select(Asset).where(Asset.first_seen >= since).order_by(Asset.first_seen.desc()).limit(8)
    ).all()
    recent_changes = [
        {"type": "asset", "value": a.value_normalized, "at": a.first_seen.isoformat()} for a in recent_assets
    ]

    activity = db.scalars(select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(10)).all()
    recent_activity = [
        {
            "action": e.action,
            "entity_type": e.entity_type,
            "entity_id": e.entity_id,
            "at": e.created_at.isoformat(),
        }
        for e in activity
    ]

    return OverviewOut(
        program_count=program_count,
        asset_count=asset_count,
        endpoint_count=endpoint_count,
        finding_count=finding_count,
        unverified_finding_count=unverified,
        active_scan_count=active_scans,
        research_queue=research_queue,
        findings_needing_verification=findings_needing_verification,
        recent_changes=recent_changes,
        recent_activity=recent_activity,
    )


@router.get("/settings")
def get_settings_view(
    db=Depends(get_db), user: User = Depends(get_current_user), settings: Settings = Depends(get_settings)
) -> dict:
    weights = None
    row = db.get(Setting, "prioritization_weights")
    if row is not None:
        weights = row.value
    tools = db.scalars(select(Tool).order_by(Tool.name)).all()
    return {
        "weights": weights,
        "evidence_max_mb": settings.evidence_max_mb,
        "evidence_retention_days": settings.evidence_retention_days,
        "tools": [
            ToolOut(name=t.name, version=t.version, available=t.available, last_checked=t.last_checked)
            for t in tools
        ],
    }


@router.put("/settings")
def update_settings(
    body: SettingsUpdate,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> dict:
    if body.weights is not None:
        row = db.get(Setting, "prioritization_weights")
        if row is None:
            row = Setting(key="prioritization_weights", value=body.weights)
            db.add(row)
        else:
            row.value = body.weights
    db.commit()
    return {"status": "ok"}


@router.post("/settings/tools/refresh")
def refresh_tools(
    db=Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
    settings: Settings = Depends(get_settings),
) -> list[ToolOut]:
    tools = detect_all(db, settings)
    return [
        ToolOut(name=t.name, version=t.version, available=t.available, last_checked=t.last_checked)
        for t in tools
    ]


@router.get("/audit")
def list_audit(
    page: int = 1,
    page_size: int = 50,
    action: str | None = None,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    stmt = select(AuditEvent)
    if action:
        stmt = stmt.where(AuditEvent.action == action)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(AuditEvent.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "total": total,
        "items": [
            {
                "id": e.id,
                "action": e.action,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "correlation_id": e.correlation_id,
                "ip": e.ip,
                "created_at": e.created_at.isoformat(),
            }
            for e in rows
        ],
    }
