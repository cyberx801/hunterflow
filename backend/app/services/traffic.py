"""Traffic service: HAR import job, manual transactions (HF-FR-070/072/076)."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import Settings
from ..core.errors import ApiError, ErrorCode
from ..core.logging import get_logger, set_correlation_id
from ..db.models import HttpTransaction, ImportJob
from ..integrations.parsers.har import HarError, parse_har
from ..integrations.tools.base import Observation

log = get_logger("hunterflow.traffic")


def _body_dir(settings: Settings, import_job_id: str) -> Path:
    d = settings.data_dir / "runs" / "imports" / import_job_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _store_body(d: Path, prefix: str, n: int, content: str | None) -> str | None:
    if not content:
        return None
    path = d / f"{prefix}_{n}.txt"
    path.write_text(content, encoding="utf-8")
    return str(path)


def run_har_import(db_factory, settings: Settings, import_job_id: str) -> None:
    set_correlation_id(f"import:{import_job_id[:8]}")
    db = db_factory()
    try:
        job = db.get(ImportJob, import_job_id)
        if job is None:
            log.error("import_job_missing", import_job_id=import_job_id)
            return
        job.status = "running"
        db.commit()
        source = Path(job.file_ref)
        counts = {"total": 0, "imported": 0, "duplicates": 0, "skipped": 0}
        d = _body_dir(settings, import_job_id)
        try:
            entries = list(parse_har(source))
        except HarError as exc:
            job.status = "failed"
            job.error_code = "PARSE_ERROR"
            job.counts = counts
            db.commit()
            log.info("import_failed", import_job_id=import_job_id, error=str(exc))
            return

        for n, entry in enumerate(entries):
            counts["total"] += 1
            existing = db.scalar(select(HttpTransaction).where(HttpTransaction.hash == entry.hash))
            if existing is not None:
                counts["duplicates"] += 1
                continue
            req_ref = _store_body(d, "req", n, entry.request_body)
            resp_ref = _store_body(d, "resp", n, entry.response_body)
            tx = HttpTransaction(
                program_id=job.program_id,
                source="har_import",
                account_tag=job.account_tag,
                method=entry.method,
                url=entry.url,
                url_host=entry.url_host,
                request_headers=entry.request_headers,
                request_body_ref=req_ref,
                response_status=entry.response_status,
                response_headers=entry.response_headers,
                response_body_ref=resp_ref,
                timing=entry.timing,
                redacted=True,
                hash=entry.hash,
            )
            db.add(tx)
            counts["imported"] += 1
            if n % 200 == 199:
                db.commit()
        job.status = "completed"
        job.counts = counts
        db.commit()
        log.info("import_completed", import_job_id=import_job_id, counts=counts)
    except Exception:
        log.exception("import_unexpected_failure", import_job_id=import_job_id)
        job = db.get(ImportJob, import_job_id)
        if job is not None:
            job.status = "failed"
            job.error_code = "JOB_ERROR"
            db.commit()
    finally:
        db.close()
        set_correlation_id(None)


def manual_transaction(db: Session, settings: Settings, body) -> HttpTransaction:
    from urllib.parse import urlsplit

    canonical = hashlib.sha256(
        (
            body.method
            + "|"
            + body.url
            + "|"
            + (body.account_tag or "")
            + "|"
            + str(body.response_status)
            + "|"
            + str(body.request_headers)
            + "|"
            + str(body.response_headers)
            + "|"
            + str(body.request_body)
            + "|"
            + str(body.response_body)
        ).encode()
    ).hexdigest()
    existing = db.scalar(select(HttpTransaction).where(HttpTransaction.hash == canonical))
    if existing is not None:
        return existing
    d = settings.data_dir / "runs" / "manual"
    d.mkdir(parents=True, exist_ok=True)
    req_ref = _store_body(d, "req", canonical[:8], body.request_body)
    resp_ref = _store_body(d, "resp", canonical[:8], body.response_body)
    tx = HttpTransaction(
        program_id=body.program_id,
        source="manual",
        account_tag=body.account_tag,
        method=body.method,
        url=body.url,
        url_host=(urlsplit(body.url).hostname or "").lower(),
        request_headers=body.request_headers,
        request_body_ref=req_ref,
        response_status=body.response_status,
        response_headers=body.response_headers,
        response_body_ref=resp_ref,
        redacted=True,
        hash=canonical,
    )
    db.add(tx)
    db.commit()
    return tx


def tx_with_bodies(db: Session, tx: HttpTransaction) -> dict:
    def read(ref):
        if not ref:
            return None
        p = Path(ref)
        return p.read_text(encoding="utf-8", errors="replace") if p.exists() else None

    return {
        "id": tx.id,
        "program_id": tx.program_id,
        "source": tx.source,
        "account_tag": tx.account_tag,
        "method": tx.method,
        "url": tx.url,
        "request_headers": tx.request_headers,
        "request_body": read(tx.request_body_ref),
        "response_status": tx.response_status,
        "response_headers": tx.response_headers,
        "response_body": read(tx.response_body_ref),
        "timing": tx.timing,
        "redacted": tx.redacted,
        "created_at": tx.created_at,
    }
