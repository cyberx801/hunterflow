"""Monitoring API: schedules and the change feed (v0.2).

All schedules run through the same scope policy enforcement as manual scans.
Notifications are opt-in per schedule and require HF_WEBHOOK_URL.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select

from ...core.audit import AuditService
from ...core.config import Settings, get_settings
from ...core.errors import ApiError, ErrorCode
from ...db.models import MonitoringEvent, ScheduledScan, User
from ...jobs.actors import enqueue_scan
from ...jobs.profiles import resolve_profile
from ...schemas.monitoring import (
    MonitoringEventOut,
    ScheduleCreate,
    ScheduleOut,
    ScheduleUpdate,
)
from ...services.programs import current_policy
from ...services.scans import create_scan_job, program_of, validate_targets
from ..deps import get_current_user, get_db, parse_uuid, require_csrf

router = APIRouter(tags=["monitoring"])


def _out(schedule: ScheduledScan) -> ScheduleOut:
    return ScheduleOut(
        id=schedule.id,
        program_id=schedule.program_id,
        profile=schedule.profile,
        interval_minutes=schedule.interval_minutes,
        enabled=schedule.enabled,
        notify=schedule.notify,
        targets=schedule.targets,
        templates=schedule.templates,
        next_run_at=schedule.next_run_at,
        last_run_at=schedule.last_run_at,
        last_job_id=schedule.last_job_id,
        created_at=schedule.created_at,
    )


@router.get("/schedules")
def list_schedules(
    program_id: str | None = None,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ScheduleOut]:
    stmt = select(ScheduledScan).order_by(ScheduledScan.created_at.desc())
    if program_id:
        stmt = stmt.where(ScheduledScan.program_id == parse_uuid(program_id))
    return [_out(s) for s in db.scalars(stmt).all()]


@router.post("/schedules", status_code=201)
def create_schedule(
    body: ScheduleCreate,
    request: Request,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_csrf),
) -> ScheduleOut:
    if body.interval_minutes < settings.min_schedule_minutes:
        raise ApiError(
            ErrorCode.VALIDATION,
            f"interval_minutes must be at least {settings.min_schedule_minutes}",
        )
    resolve_profile(body.profile, body.templates)  # validates curated templates
    program = program_of(db, parse_uuid(body.program_id))
    validate_targets(current_policy(db, program), body.targets)

    schedule = ScheduledScan(
        program_id=program.id,
        profile=body.profile,
        interval_minutes=body.interval_minutes,
        enabled=body.enabled,
        targets=body.targets,
        templates=body.templates,
        notify=body.notify,
        next_run_at=datetime.now(UTC),  # due immediately; scheduler picks it up
        created_by=user.id,
    )
    db.add(schedule)
    db.flush()
    AuditService.record(
        db,
        "schedule.created",
        "scheduled_scan",
        schedule.id,
        after={"profile": schedule.profile, "interval_minutes": schedule.interval_minutes},
        actor_id=user.id,
        ip=request.client.host if request.client else None,
    )
    db.commit()
    return _out(schedule)


@router.patch("/schedules/{schedule_id}")
def update_schedule(
    schedule_id: str,
    body: ScheduleUpdate,
    request: Request,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_csrf),
) -> ScheduleOut:
    schedule = db.get(ScheduledScan, parse_uuid(schedule_id))
    if schedule is None:
        raise ApiError(ErrorCode.NOT_FOUND, "Schedule not found", 404)
    data = body.model_dump(exclude_unset=True)
    if "interval_minutes" in data and data["interval_minutes"] < settings.min_schedule_minutes:
        raise ApiError(
            ErrorCode.VALIDATION,
            f"interval_minutes must be at least {settings.min_schedule_minutes}",
        )
    if "targets" in data and data["targets"] is not None:
        program = program_of(db, schedule.program_id)
        validate_targets(current_policy(db, program), data["targets"])
    if "templates" in data and data["templates"] is not None:
        resolve_profile(schedule.profile, data["templates"])
    for key, value in data.items():
        setattr(schedule, key, value)
    AuditService.record(
        db, "schedule.updated", "scheduled_scan", schedule.id, actor_id=user.id,
        ip=request.client.host if request.client else None,
    )
    db.commit()
    return _out(schedule)


@router.delete("/schedules/{schedule_id}")
def delete_schedule(
    schedule_id: str,
    request: Request,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> dict:
    schedule = db.get(ScheduledScan, parse_uuid(schedule_id))
    if schedule is None:
        raise ApiError(ErrorCode.NOT_FOUND, "Schedule not found", 404)
    db.delete(schedule)
    AuditService.record(db, "schedule.deleted", "scheduled_scan", schedule.id, actor_id=user.id)
    db.commit()
    return {"status": "ok"}


@router.post("/schedules/{schedule_id}/run-now", status_code=202)
def run_schedule_now(
    schedule_id: str,
    request: Request,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> dict:
    schedule = db.get(ScheduledScan, parse_uuid(schedule_id))
    if schedule is None:
        raise ApiError(ErrorCode.NOT_FOUND, "Schedule not found", 404)
    job = create_scan_job(
        db,
        program_id=schedule.program_id,
        profile=schedule.profile,
        targets=schedule.targets or [],
        templates=schedule.templates or [],
        dry_run=False,
        actor_id=user.id,
        schedule_id=schedule.id,
    )
    enqueue_scan(job.id)
    schedule.last_run_at = datetime.now(UTC)
    schedule.last_job_id = job.id
    db.commit()
    return {"job_id": job.id, "status": "queued"}


@router.get("/monitoring/events")
def list_events(
    program_id: str | None = None,
    kind: str | None = None,
    limit: int = 100,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[MonitoringEventOut]:
    stmt = select(MonitoringEvent).order_by(MonitoringEvent.created_at.desc()).limit(min(limit, 500))
    if program_id:
        stmt = stmt.where(MonitoringEvent.program_id == parse_uuid(program_id))
    if kind:
        stmt = stmt.where(MonitoringEvent.kind == kind)
    rows = db.scalars(stmt).all()
    return [
        MonitoringEventOut(
            id=e.id,
            program_id=e.program_id,
            scan_job_id=e.scan_job_id,
            kind=e.kind,
            entity_type=e.entity_type,
            entity_id=e.entity_id,
            entity_value=e.entity_value,
            detail=e.detail,
            created_at=e.created_at,
        )
        for e in rows
    ]


@router.get("/monitoring/status")
def monitoring_status(
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> dict:
    return {
        "webhook_configured": bool(settings.webhook_url),
        "scheduler_interval_seconds": settings.scheduler_interval_seconds,
        "min_schedule_minutes": settings.min_schedule_minutes,
    }
