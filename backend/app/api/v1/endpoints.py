"""Endpoints API (HF-FR-052)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select

from ...core.errors import ApiError, ErrorCode
from ...db.models import Asset, Endpoint, ResearchCard, User
from ...schemas.inventory import EndpointOut, EndpointUpdate
from ..deps import get_current_user, get_db, parse_uuid, require_csrf
from ._common import ListParams, Page, paginate
from ...services.assets import endpoint_priority

router = APIRouter(tags=["endpoints"])


def _out(db, endpoint: Endpoint) -> EndpointOut:
    card_count = db.scalar(
        select(func.count()).select_from(ResearchCard).where(ResearchCard.endpoint_id == endpoint.id)
    ) or 0
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
    items = [_out(db, e) for e in rows]
    if auth_only:
        items = [i for i in items if (i.auth_indicators or {}).get("auth_challenge")]
        total = len(items)
    if params.sort == "priority":
        items.sort(key=lambda i: i.priority_score, reverse=True)
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.get("/endpoints/{endpoint_id}")
def get_endpoint(
    endpoint_id: str, db=Depends(get_db), user: User = Depends(get_current_user)
) -> EndpointOut:
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
