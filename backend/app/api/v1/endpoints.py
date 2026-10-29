"""Endpoints API (HF-FR-052)."""

from __future__ import annotations

from datetime import UTC

from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from ...core.errors import ApiError, ErrorCode
from ...db.models import Asset, Endpoint, ResearchCard, User
from ...schemas.inventory import EndpointOut, EndpointUpdate
from ...services.assets import endpoint_priority
from ..deps import get_current_user, get_db, parse_uuid, require_csrf
from ._common import ListParams, Page, paginate

router = APIRouter(tags=["endpoints"])


def _out(db, endpoint: Endpoint) -> EndpointOut:
    card_count = (
        db.scalar(select(func.count()).select_from(ResearchCard).where(ResearchCard.endpoint_id == endpoint.id)) or 0
    )
    priority, _ = endpoint_priority(db, endpoint)
    asset = db.get(Asset, endpoint.asset_id)
    return EndpointOut(
        id=endpoint.id,
        program_id=endpoint.program_id,
        asset_id=endpoint.asset_id,
        method=endpoint.method,
        path=endpoint.path,
        category=endpoint.category,
        category_manual=endpoint.category_manual,
        auth_indicators=endpoint.auth_indicators,
        status_distribution=endpoint.status_distribution,
        content_types=endpoint.content_types,
        first_seen=endpoint.first_seen,
        last_seen=endpoint.last_seen,
        card_count=card_count,
        priority_score=priority,
        asset_value=asset.value_normalized if asset else None,
    )


def _out_batched(db, endpoint: Endpoint, card_count: int, finding_count: int, asset_value: str | None) -> EndpointOut:
    from datetime import datetime, timedelta

    from ...db.base import ensure_utc
    from ...domain.scoring import score

    now = datetime.now(UTC)
    signals = {
        "new_endpoint": (now - ensure_utc(endpoint.first_seen)) < timedelta(days=7),
        "auth_sensitive": bool((endpoint.auth_indicators or {}).get("auth_challenge"))
        or endpoint.category in ("auth", "account", "admin", "payment"),
        "scanner_observation": finding_count > 0,
        "untested": card_count == 0,
    }
    priority = score(signals).score
    return EndpointOut(
        id=endpoint.id,
        program_id=endpoint.program_id,
        asset_id=endpoint.asset_id,
        method=endpoint.method,
        path=endpoint.path,
        category=endpoint.category,
        category_manual=endpoint.category_manual,
        auth_indicators=endpoint.auth_indicators,
        status_distribution=endpoint.status_distribution,
        content_types=endpoint.content_types,
        first_seen=endpoint.first_seen,
        last_seen=endpoint.last_seen,
        card_count=card_count,
        priority_score=priority,
        asset_value=asset_value,
    )


@router.get("/endpoints")
def list_endpoints(
    params: ListParams = Depends(),
    program_id: str | None = None,
    method: str | None = None,
    category: str | None = None,
    auth_only: bool = False,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
) -> Page[EndpointOut]:
    from sqlalchemy import func

    from ...db.models import Finding

    stmt = select(Endpoint)
    if program_id:
        stmt = stmt.where(Endpoint.program_id == parse_uuid(program_id))
    if method:
        stmt = stmt.where(Endpoint.method == method.upper())
    if category:
        stmt = stmt.where(Endpoint.category == category)
    if params.q:
        like = f"%{params.q}%"
        stmt = stmt.where(Endpoint.path.ilike(like))
    rows, total = paginate(db, stmt, params.page, params.page_size, Endpoint.last_seen.desc())

    endpoint_ids = [e.id for e in rows]
    asset_values: dict[str, str] = {}
    card_counts: dict[str, int] = {}
    finding_counts: dict[str, int] = {}
    if endpoint_ids:
        asset_ids = {e.asset_id for e in rows}
        asset_values = dict(db.execute(select(Asset.id, Asset.value_normalized).where(Asset.id.in_(asset_ids))).all())
        card_counts = dict(
            db.execute(
                select(ResearchCard.endpoint_id, func.count())
                .where(ResearchCard.endpoint_id.in_(endpoint_ids))
                .group_by(ResearchCard.endpoint_id)
            ).all()
        )
        finding_counts = dict(
            db.execute(
                select(Finding.endpoint_id, func.count())
                .where(Finding.endpoint_id.in_(endpoint_ids))
                .group_by(Finding.endpoint_id)
            ).all()
        )

    items = [
        _out_batched(db, e, card_counts.get(e.id, 0), finding_counts.get(e.id, 0), asset_values.get(e.asset_id))
        for e in rows
    ]
    if auth_only:
        items = [i for i in items if (i.auth_indicators or {}).get("auth_challenge")]
        total = len(items)
    if params.sort == "priority":
        items.sort(key=lambda i: i.priority_score, reverse=True)
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.get("/endpoints/{endpoint_id}")
def get_endpoint(endpoint_id: str, db=Depends(get_db), user: User = Depends(get_current_user)) -> EndpointOut:
    endpoint = db.get(Endpoint, parse_uuid(endpoint_id))
    if endpoint is None:
        raise ApiError(ErrorCode.NOT_FOUND, "Endpoint not found", 404)
    return _out(db, endpoint)


@router.patch("/endpoints/{endpoint_id}")
def update_endpoint(
    endpoint_id: str,
    body: EndpointUpdate,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> EndpointOut:
    endpoint = db.get(Endpoint, parse_uuid(endpoint_id))
    if endpoint is None:
        raise ApiError(ErrorCode.NOT_FOUND, "Endpoint not found", 404)
    endpoint.category = body.category
    endpoint.category_manual = True
    db.commit()
    return _out(db, endpoint)
