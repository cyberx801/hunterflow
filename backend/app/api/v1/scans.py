"""Scans and jobs API (HF-FR-023/024/025/028)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select

from ...core.audit import AuditService
from ...core.errors import ApiError, ErrorCode
from ...core.redaction import redact_text
from ...db.models import PolicyVersion, ScanJob, ToolRun, User
from ...jobs.actors import enqueue_scan
from ...jobs.profiles import CURATED_TEMPLATES, PROFILES
from ...schemas.scans import (
    CuratedTemplateOut,
    JobOut,
    ScanCreate,
    ScanOut,
    ScanProfileOut,
    ToolRunOut,
)
from ...services import scans as scans_service
from ..deps import get_current_user, get_db, parse_uuid, require_csrf
from ._common import ListParams, Page, paginate

router = APIRouter(tags=["scans"])


def _scan_out(job: ScanJob) -> ScanOut:
    return ScanOut(
        id=job.id,
        program_id=job.program_id,
        profile=job.profile,
        status=job.status,
        dry_run=job.dry_run,
        error_code=job.error_code,
        progress=job.progress,
        started_at=job.started_at,
        finished_at=job.finished_at,
        created_at=job.created_at,
    )


@router.get("/profiles")
def list_profiles(user: User = Depends(get_current_user)) -> list[ScanProfileOut]:
    return [
        ScanProfileOut(
            id=key,
            label=spec["label"],
            description=spec["description"],
            steps=[s["tool"] for s in spec["steps"]],
            requires_templates=spec.get("requires_templates", False),
        )
        for key, spec in PROFILES.items()
    ]


@router.get("/profiles/curated-templates")
def list_curated_templates(user: User = Depends(get_current_user)) -> list[CuratedTemplateOut]:
    out = []
    for category, templates in CURATED_TEMPLATES.items():
        for tid, meta in templates.items():
            out.append(CuratedTemplateOut(id=tid, name=meta["name"], severity=meta["severity"], category=category))
    return out


@router.get("/scans")
def list_scans(
    params: ListParams = Depends(),
    program_id: str | None = None,
    status: str | None = None,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
) -> Page[ScanOut]:
    stmt = select(ScanJob)
    if program_id:
        stmt = stmt.where(ScanJob.program_id == parse_uuid(program_id))
    if status:
        stmt = stmt.where(ScanJob.status == status)
    rows, total = paginate(db, stmt, params.page, params.page_size, ScanJob.created_at.desc())
    return Page(items=[_scan_out(j) for j in rows], total=total, page=params.page, page_size=params.page_size)


@router.post("/scans", status_code=202)
def create_scan(
    body: ScanCreate,
    request: Request,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> ScanOut:
    job = scans_service.create_scan_job(
        db,
        program_id=parse_uuid(body.program_id),
        profile=body.profile,
        targets=body.targets,
        templates=body.templates,
        dry_run=body.dry_run,
        actor_id=user.id,
        ip=request.client.host if request.client else None,
    )
    if body.dry_run:
        # Dry-run performs zero tool/network work; execute synchronously so it
        # works even without a broker (pure planning operation).
        from ...core.config import get_settings
        from ...jobs.pipeline import run_scan_job

        factory = request.app.state.session_factory
        run_scan_job(factory, get_settings(), job.id)
    else:
        enqueue_scan(job.id)
    db.refresh(job)
    return _scan_out(job)


@router.get("/jobs/{job_id}")
def get_job(job_id: str, db=Depends(get_db), user: User = Depends(get_current_user)) -> JobOut:
    job = db.get(ScanJob, parse_uuid(job_id))
    if job is None:
        raise ApiError(ErrorCode.NOT_FOUND, "Job not found", 404)
    policy_version = None
    if job.policy_version_id:
        pv = db.get(PolicyVersion, job.policy_version_id)
        if pv is not None:
            policy_version = pv.version
    runs = db.scalars(select(ToolRun).where(ToolRun.scan_job_id == job.id).order_by(ToolRun.started_at)).all()
    return JobOut(
        **_scan_out(job).model_dump(),
        policy_version=policy_version,
        tool_runs=[
            ToolRunOut(
                id=r.id,
                tool=r.tool,
                version=r.version,
                args=r.args or [],
                exit_code=r.exit_code,
                status=r.status,
                timeout_seconds=r.timeout_seconds,
                started_at=r.started_at,
                finished_at=r.finished_at,
            )
            for r in runs
        ],
    )


@router.post("/jobs/{job_id}/cancel")
def cancel_job(
    job_id: str,
    request: Request,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> dict:
    job = db.get(ScanJob, parse_uuid(job_id))
    if job is None:
        raise ApiError(ErrorCode.NOT_FOUND, "Job not found", 404)
    job.cancel_requested = True
    AuditService.record(db, "scan.cancel_requested", "scan_job", job.id, actor_id=user.id)
    db.commit()
    return {"status": "ok"}


@router.get("/jobs/{job_id}/runs/{run_id}/output")
def tool_run_output(
    job_id: str,
    run_id: str,
    stream: str = "stdout",
    db=Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    run = db.get(ToolRun, parse_uuid(run_id))
    if run is None or run.scan_job_id != parse_uuid(job_id):
        raise ApiError(ErrorCode.NOT_FOUND, "Tool run not found", 404)
    path = run.stdout_ref if stream == "stdout" else run.stderr_ref
    content = ""
    if path:
        from pathlib import Path

        p = Path(path)
        if p.exists():
            raw = p.read_bytes()[-1024 * 512 :]  # tail, 512KB cap
            content = redact_text(raw.decode("utf-8", "replace"))
    return {"content": content, "truncated": True}
