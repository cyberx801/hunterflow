"""Evidence API: secure upload, integrity, authenticated download, links
(HF-FR-090/091, HF-SEC-008/009)."""

from __future__ import annotations

import hashlib
import mimetypes
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select

from ...core.config import Settings, get_settings
from ...core.audit import AuditService
from ...core.errors import ApiError, ErrorCode
from ...db.models import EvidenceFile, EvidenceLink, Finding, ResearchCard, User
from ...schemas.findings import EvidenceOut
from ..deps import get_current_user, get_db, parse_uuid, require_csrf

router = APIRouter(tags=["evidence"])

ALLOWED_EXTENSIONS = {".txt", ".md", ".json", ".har", ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".csv", ".html"}
ALLOWED_MIME_PREFIX = ("text/", "image/", "application/json", "application/pdf", "application/octet-stream")
MAGIC_SIGNATURES = {
    b"\x89PNG\r\n\x1a\n": ".png",
    b"\xff\xd8\xff": ".jpg",
    b"%PDF-": ".pdf",
    b"GIF8": ".gif",
}


def _magic_ext(head: bytes) -> str | None:
    for sig, ext in MAGIC_SIGNATURES.items():
        if head.startswith(sig):
            return ext
    return None


@router.post("/evidence", status_code=201)
def upload_evidence(
    request: Request,
    program_id: str | None = None,
    finding_id: str | None = None,
    card_id: str | None = None,
    file: UploadFile = File(...),
    db=Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
    settings: Settings = Depends(get_settings),
) -> EvidenceOut:
    filename = file.filename or "unnamed"
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ApiError(ErrorCode.UPLOAD_REJECTED, f"File type not allowed: {ext or '(none)'}")
    max_bytes = settings.evidence_max_mb * 1024 * 1024
    data = file.file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ApiError(
            ErrorCode.UPLOAD_REJECTED, f"File exceeds {settings.evidence_max_mb} MB limit"
        )
    magic = _magic_ext(data[:16])
    if magic is not None and magic != ext:
        raise ApiError(ErrorCode.UPLOAD_REJECTED, "File content does not match extension")

    sha = hashlib.sha256(data).hexdigest()
    stored_dir = settings.data_dir / "evidence" / sha[:2]
    stored_dir.mkdir(parents=True, exist_ok=True)
    stored_path = stored_dir / f"{sha}{ext}"
    tmp = stored_dir / f"{uuid.uuid4().hex}.tmp"
    tmp.write_bytes(data)
    tmp.replace(stored_path)  # atomic

    pid = parse_uuid(program_id) if program_id else None
    mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    record = EvidenceFile(
        program_id=pid,
        filename=filename,
        stored_path=str(stored_path),
        sha256=sha,
        size=len(data),
        mime=mime,
        redacted=False,
        retention_days=settings.evidence_retention_days or None,
    )
    db.add(record)
    db.flush()
    if finding_id or card_id:
        link = EvidenceLink(
            evidence_id=record.id,
            finding_id=parse_uuid(finding_id) if finding_id else None,
            card_id=parse_uuid(card_id) if card_id else None,
        )
        db.add(link)
    AuditService.record(
        db, "evidence.uploaded", "evidence", record.id,
        after={"filename": filename, "size": len(data), "sha256": sha}, actor_id=user.id,
    )
    db.commit()
    return EvidenceOut(
        id=record.id,
        program_id=record.program_id,
        filename=record.filename,
        sha256=record.sha256,
        size=record.size,
        mime=record.mime,
        redacted=record.redacted,
        created_at=record.created_at,
    )


@router.get("/evidence")
def list_evidence(
    program_id: str | None = None,
    finding_id: str | None = None,
    card_id: str | None = None,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[EvidenceOut]:
    stmt = select(EvidenceFile).order_by(EvidenceFile.created_at.desc())
    if program_id:
        stmt = stmt.where(EvidenceFile.program_id == parse_uuid(program_id))
    rows = db.scalars(stmt).all()
    out = [
        EvidenceOut(
            id=e.id, program_id=e.program_id, filename=e.filename, sha256=e.sha256,
            size=e.size, mime=e.mime, redacted=e.redacted, created_at=e.created_at,
        )
        for e in rows
    ]
    if finding_id or card_id:
        linked = db.scalars(
            select(EvidenceLink).where(
                EvidenceLink.finding_id == (parse_uuid(finding_id) if finding_id else None),
            )
        ).all() if finding_id else []
        if card_id:
            linked = db.scalars(
                select(EvidenceLink).where(EvidenceLink.card_id == parse_uuid(card_id))
            ).all()
        ids = {l.evidence_id for l in linked}
        out = [e for e in out if e.id in ids]
    return out


@router.get("/evidence/{evidence_id}/download")
def download_evidence(
    evidence_id: str,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
) -> FileResponse:
    record = db.get(EvidenceFile, parse_uuid(evidence_id))
    if record is None:
        raise ApiError(ErrorCode.NOT_FOUND, "Evidence not found", 404)
    path = Path(record.stored_path)
    if not path.exists():
        raise ApiError(ErrorCode.NOT_FOUND, "Evidence file missing on disk", 404)
    # Integrity check (HF-FR-090).
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != record.sha256:
        raise ApiError(ErrorCode.INTERNAL, "Evidence integrity check failed", 500)
    AuditService.record(db, "evidence.downloaded", "evidence", record.id, actor_id=user.id)
    db.commit()
    return FileResponse(
        path, media_type=record.mime, filename=record.filename, content_disposition_type="attachment"
    )


@router.post("/evidence/{evidence_id}/links")
def link_evidence(
    evidence_id: str,
    body: dict,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> dict:
    record = db.get(EvidenceFile, parse_uuid(evidence_id))
    if record is None:
        raise ApiError(ErrorCode.NOT_FOUND, "Evidence not found", 404)
    finding_id = body.get("finding_id")
    card_id = body.get("card_id")
    link = EvidenceLink(
        evidence_id=record.id,
        finding_id=parse_uuid(finding_id) if finding_id else None,
        card_id=parse_uuid(card_id) if card_id else None,
    )
    db.add(link)
    db.commit()
    return {"status": "ok"}


@router.delete("/evidence/{evidence_id}")
def delete_evidence(
    evidence_id: str,
    request: Request,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> dict:
    record = db.get(EvidenceFile, parse_uuid(evidence_id))
    if record is None:
        raise ApiError(ErrorCode.NOT_FOUND, "Evidence not found", 404)
    db.query(EvidenceLink).filter(EvidenceLink.evidence_id == record.id).delete()
    db.delete(record)
    AuditService.record(db, "evidence.deleted", "evidence", record.id, actor_id=user.id)
    db.commit()
    Path(record.stored_path).unlink(missing_ok=True)
    return {"status": "ok"}
