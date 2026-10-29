"""Reports API (HF-FR-100/101)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select

from ...core.config import Settings, get_settings
from ...core.errors import ApiError, ErrorCode
from ...db.models import Finding, Report, User
from ...schemas.findings import ReportCreate, ReportOut
from ...services import reports as reports_service
from ..deps import get_current_user, get_db, parse_uuid, require_csrf

router = APIRouter(tags=["reports"])


@router.post("/reports", status_code=201)
def generate_report(
    body: ReportCreate,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
    settings: Settings = Depends(get_settings),
) -> ReportOut:
    finding = db.get(Finding, parse_uuid(body.finding_id))
    if finding is None:
        raise ApiError(ErrorCode.NOT_FOUND, "Finding not found", 404)
    content, path = reports_service.generate(db, finding, body.format, settings)
    report = Report(
        program_id=finding.program_id,
        finding_id=finding.id,
        format=body.format,
        content_ref=str(path),
    )
    db.add(report)
    db.commit()
    return ReportOut(
        id=report.id, finding_id=finding.id, format=body.format,
        generated_at=report.generated_at, content=content,
    )


@router.get("/reports")
def list_reports(db=Depends(get_db), user: User = Depends(get_current_user)) -> list[ReportOut]:
    rows = db.scalars(select(Report).order_by(Report.generated_at.desc()).limit(100)).all()
    return [
        ReportOut(id=r.id, finding_id=r.finding_id, format=r.format, generated_at=r.generated_at)
        for r in rows
    ]


@router.get("/reports/{report_id}")
def get_report(report_id: str, db=Depends(get_db), user: User = Depends(get_current_user)) -> ReportOut:
    report = db.get(Report, parse_uuid(report_id))
    if report is None:
        raise ApiError(ErrorCode.NOT_FOUND, "Report not found", 404)
    from pathlib import Path

    content = None
    p = Path(report.content_ref)
    if p.exists():
        content = p.read_text(encoding="utf-8")
    return ReportOut(
        id=report.id, finding_id=report.finding_id, format=report.format,
        generated_at=report.generated_at, content=content,
    )
