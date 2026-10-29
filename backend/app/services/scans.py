"""Scan job creation: policy pre-flight, validation, concurrency (HF-FR-023/027)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.audit import AuditService
from ..core.errors import ApiError, ErrorCode
from ..db.models import JobStatus, ScanJob
from ..domain.scope import Policy
from ..jobs.profiles import CURATED_TEMPLATES, PROFILES, resolve_profile
from .programs import current_policy, latest_policy_version


def validate_targets(policy: Policy, targets: list[str]) -> None:
    if not targets:
        return
    for target in targets:
        decision = policy.evaluate_url(target) if "://" in target else policy.evaluate(target)
        if not decision.allowed:
            raise ApiError(
                ErrorCode.SCOPE_DENIED,
                f"Target '{target}' is not authorized by the current policy",
                400,
                details={"reason": decision.reason},
            )


def running_job_count(db: Session, program_id: str) -> int:
    return db.scalar(
        select(ScanJob.id).where(
            ScanJob.program_id == program_id,
            ScanJob.status.in_([JobStatus.queued.value, JobStatus.running.value]),
        ).limit(1)
    ) is not None and 1 or 0


def create_scan_job(
    db: Session,
    program_id: str,
    profile: str,
    targets: list[str] | None,
    templates: list[str] | None,
    dry_run: bool,
    actor_id: str | None = None,
    ip: str | None = None,
) -> ScanJob:
    if profile not in PROFILES:
        raise ApiError(ErrorCode.VALIDATION, f"Unknown profile: {profile}")
    spec = resolve_profile(profile, templates)

    policy = current_policy(db, program_of(db, program_id))
    validate_targets(policy, targets or [])

    if running_job_count(db, program_id) > 0:
        raise ApiError(
            ErrorCode.CONFLICT,
            "A scan is already queued or running for this program",
            409,
        )

    version_id = None
    pv_rows = db.scalars(
        select(__import__("app.db.models", fromlist=["PolicyVersion"]).PolicyVersion)
        .where(__import__("app.db.models", fromlist=["PolicyVersion"]).PolicyVersion.program_id == program_id)
        .order_by(__import__("app.db.models", fromlist=["PolicyVersion"]).PolicyVersion.version.desc())
        .limit(1)
    ).all()
    if pv_rows:
        version_id = pv_rows[0].id

    job = ScanJob(
        program_id=program_id,
        profile=profile,
        policy_version_id=version_id,
        target_filter={"targets": targets or [], "templates": templates or []},
        dry_run=dry_run,
        status=JobStatus.queued.value,
        created_by=actor_id,
    )
    db.add(job)
    db.flush()
    AuditService.record(
        db, "scan.created", "scan_job", job.id,
        after={"profile": profile, "dry_run": dry_run},
        actor_id=actor_id, ip=ip,
    )
    db.commit()
    return job


def program_of(db: Session, program_id: str):
    from ..db.models import Program

    program = db.get(Program, program_id)
    if program is None:
        raise ApiError(ErrorCode.NOT_FOUND, "Program not found", 404)
    return program
