"""Traffic API: HAR import, transactions, comparisons (HF-FR-070..075)."""

from __future__ import annotations

import shutil
import uuid

from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy import select

from ...core.config import Settings, get_settings
from ...core.errors import ApiError, ErrorCode
from ...db.models import (
    ComparisonMember,
    ComparisonSet,
    HttpTransaction,
    ImportJob,
    NormalizationProfile,
    User,
)
from ...domain.compare import NormalizationProfile as NP
from ...domain.compare import compare as run_compare
from ...jobs.actors import enqueue_import
from ...schemas.inventory import (
    ComparisonCreate,
    ComparisonOut,
    ManualTransactionCreate,
    NormalizationProfileOut,
    TransactionOut,
)
from ...services import traffic as traffic_service
from ..deps import get_current_user, get_db, parse_uuid, require_csrf
from ._common import ListParams, Page, paginate

router = APIRouter(tags=["traffic"])


@router.post("/traffic/import", status_code=202)
def import_har(
    request: Request,
    account_tag: str | None = None,
    program_id: str | None = None,
    file: UploadFile = File(...),
    db=Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
    settings: Settings = Depends(get_settings),
) -> dict:
    if program_id is None:
        raise ApiError(ErrorCode.VALIDATION, "program_id query parameter is required")
    pid = parse_uuid(program_id)
    if not (file.filename or "").lower().endswith((".har", ".json")):
        raise ApiError(ErrorCode.UPLOAD_REJECTED, "Only .har files are accepted")
    uploads = settings.data_dir / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    target = uploads / f"{uuid.uuid4().hex}.har"
    with target.open("wb") as out:
        shutil.copyfileobj(file.file, out, length=1024 * 1024)
    if target.stat().st_size > 50 * 1024 * 1024:
        target.unlink(missing_ok=True)
        raise ApiError(ErrorCode.UPLOAD_REJECTED, "HAR file too large (max 50 MB)")
    job = ImportJob(program_id=pid, kind="har", file_ref=str(target), account_tag=account_tag)
    db.add(job)
    db.commit()
    enqueue_import(job.id)
    db.refresh(job)
    return {"import_job_id": job.id, "status": job.status}


@router.get("/traffic/imports")
def list_imports(
    program_id: str | None = None,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict]:
    stmt = select(ImportJob).order_by(ImportJob.created_at.desc()).limit(50)
    if program_id:
        stmt = stmt.where(ImportJob.program_id == parse_uuid(program_id))
    jobs = db.scalars(stmt).all()
    return [
        {
            "id": j.id,
            "program_id": j.program_id,
            "account_tag": j.account_tag,
            "status": j.status,
            "counts": j.counts,
            "error_code": j.error_code,
            "created_at": j.created_at.isoformat(),
        }
        for j in jobs
    ]


@router.get("/traffic/transactions")
def list_transactions(
    params: ListParams = Depends(),
    program_id: str | None = None,
    host: str | None = None,
    method: str | None = None,
    status: int | None = None,
    account_tag: str | None = None,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
) -> Page[TransactionOut]:
    stmt = select(HttpTransaction)
    if program_id:
        stmt = stmt.where(HttpTransaction.program_id == parse_uuid(program_id))
    if host:
        stmt = stmt.where(HttpTransaction.url_host == host.lower())
    if method:
        stmt = stmt.where(HttpTransaction.method == method.upper())
    if status is not None:
        stmt = stmt.where(HttpTransaction.response_status == status)
    if account_tag:
        stmt = stmt.where(HttpTransaction.account_tag == account_tag)
    if params.q:
        like = f"%{params.q}%"
        stmt = stmt.where(HttpTransaction.url.ilike(like))
    rows, total = paginate(db, stmt, params.page, params.page_size, HttpTransaction.created_at.desc())
    return Page(
        items=[
            TransactionOut(
                id=t.id,
                program_id=t.program_id,
                source=t.source,
                account_tag=t.account_tag,
                method=t.method,
                url=t.url,
                response_status=t.response_status,
                redacted=t.redacted,
                created_at=t.created_at,
            )
            for t in rows
        ],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get("/traffic/transactions/{tx_id}")
def get_transaction(tx_id: str, db=Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    tx = db.get(HttpTransaction, parse_uuid(tx_id))
    if tx is None:
        raise ApiError(ErrorCode.NOT_FOUND, "Transaction not found", 404)
    return traffic_service.tx_with_bodies(db, tx)


@router.post("/traffic/transactions")
def create_manual_transaction(
    body: ManualTransactionCreate,
    request: Request,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
    settings: Settings = Depends(get_settings),
) -> TransactionOut:
    tx = traffic_service.manual_transaction(db, settings, body)
    return TransactionOut(
        id=tx.id,
        program_id=tx.program_id,
        source=tx.source,
        account_tag=tx.account_tag,
        method=tx.method,
        url=tx.url,
        response_status=tx.response_status,
        redacted=tx.redacted,
        created_at=tx.created_at,
    )


@router.post("/comparisons")
def create_comparison(
    body: ComparisonCreate,
    request: Request,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> ComparisonOut:
    ids = [parse_uuid(i) for i in body.transaction_ids]
    txs = db.scalars(select(HttpTransaction).where(HttpTransaction.id.in_(ids))).all()
    if len(txs) != len(set(ids)):
        raise ApiError(ErrorCode.VALIDATION, "One or more transactions not found")
    cs = ComparisonSet(program_id=parse_uuid(body.program_id), name=body.name)
    db.add(cs)
    db.flush()
    for position, tid in enumerate(ids):
        db.add(ComparisonMember(set_id=cs.id, transaction_id=tid, position=position))
    db.commit()
    return ComparisonOut(
        id=cs.id,
        program_id=cs.program_id,
        name=cs.name,
        created_at=cs.created_at,
        member_count=len(ids),
    )


@router.get("/comparisons")
def list_comparisons(
    program_id: str | None = None,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ComparisonOut]:
    stmt = select(ComparisonSet).order_by(ComparisonSet.created_at.desc())
    if program_id:
        stmt = stmt.where(ComparisonSet.program_id == parse_uuid(program_id))
    sets = db.scalars(stmt).all()
    out = []
    for cs in sets:
        count = (
            db.scalar(
                select(__import__("sqlalchemy").func.count())
                .select_from(ComparisonMember)
                .where(ComparisonMember.set_id == cs.id)
            )
            or 0
        )
        out.append(
            ComparisonOut(
                id=cs.id, program_id=cs.program_id, name=cs.name, created_at=cs.created_at, member_count=count
            )
        )
    return out


@router.get("/comparisons/{set_id}")
def get_comparison(set_id: str, db=Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    cs = db.get(ComparisonSet, parse_uuid(set_id))
    if cs is None:
        raise ApiError(ErrorCode.NOT_FOUND, "Comparison not found", 404)
    members = db.scalars(
        select(ComparisonMember).where(ComparisonMember.set_id == cs.id).order_by(ComparisonMember.position)
    ).all()
    tx_data = []
    for m in members:
        tx = db.get(HttpTransaction, m.transaction_id)
        if tx is not None:
            tx_data.append(traffic_service.tx_with_bodies(db, tx))
    profile = NP()
    result = run_compare(tx_data, profile)
    return {
        "id": cs.id,
        "name": cs.name,
        "panes": [
            {
                "label": p.label,
                "method": p.method,
                "url": p.url,
                "request_headers": p.request_headers,
                "request_body": p.request_body,
                "status": p.status,
                "response_headers": p.response_headers,
                "response_body": p.response_body,
            }
            for p in result.panes
        ],
        "body_diff": [{"kind": d.kind, "left": d.left, "right": d.right} for d in result.body_diff],
        "header_diff": result.header_diff,
        "status_diff": result.status_diff,
        "review_required": result.review_required,
        "review_reason": result.review_reason,
    }


@router.delete("/comparisons/{set_id}")
def delete_comparison(
    set_id: str,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> dict:
    cs = db.get(ComparisonSet, parse_uuid(set_id))
    if cs is None:
        raise ApiError(ErrorCode.NOT_FOUND, "Comparison not found", 404)
    db.query(ComparisonMember).filter(ComparisonMember.set_id == cs.id).delete()
    db.delete(cs)
    db.commit()
    return {"status": "ok"}


@router.get("/normalization-profiles")
def list_normalization_profiles(
    db=Depends(get_db), user: User = Depends(get_current_user)
) -> list[NormalizationProfileOut]:
    rows = db.scalars(select(NormalizationProfile).order_by(NormalizationProfile.created_at)).all()
    return [
        NormalizationProfileOut(id=p.id, name=p.name, ignore_headers=p.ignore_headers, dynamic_rules=p.dynamic_rules)
        for p in rows
    ]
