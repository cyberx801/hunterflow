"""Assets API (HF-FR-043/044)."""

from __future__ import annotations

from datetime import UTC

from fastapi import APIRouter, Depends
from sqlalchemy import or_, select

from ...db.models import Asset, User
from ...schemas.inventory import AssetOut, AssetUpdate
from ...services.assets import asset_priority, counts_for
from ..deps import get_current_user, get_db, parse_uuid, require_csrf
from ._common import ListParams, Page, paginate

router = APIRouter(tags=["assets"])


def _out(db, asset: Asset) -> AssetOut:
    endpoint_count, card_count = counts_for(db, asset.program_id, asset.id)
    priority, _ = asset_priority(db, asset)
    return AssetOut(
        id=asset.id,
        program_id=asset.program_id,
        type=asset.type,
        value_normalized=asset.value_normalized,
        value_original=asset.value_original,
        scope_status=asset.scope_status,
        http_status=asset.http_status,
        tech=asset.tech,
        tags=asset.tags,
        notes=asset.notes,
        first_seen=asset.first_seen,
        last_seen=asset.last_seen,
        endpoint_count=endpoint_count,
        card_count=card_count,
        priority_score=priority,
    )


def _out_batched(db, asset: Asset, endpoint_count: int, card_count: int) -> AssetOut:
    from datetime import datetime, timedelta

    from ...db.base import ensure_utc
    from ...domain.scoring import score

    now = datetime.now(UTC)
    signals = {
        "new_asset": (now - ensure_utc(asset.first_seen)) < timedelta(days=7),
        "untested": card_count == 0 and endpoint_count > 0,
    }
    priority = score(signals).score
    return AssetOut(
        id=asset.id,
        program_id=asset.program_id,
        type=asset.type,
        value_normalized=asset.value_normalized,
        value_original=asset.value_original,
        scope_status=asset.scope_status,
        http_status=asset.http_status,
        tech=asset.tech,
        tags=asset.tags,
        notes=asset.notes,
        first_seen=asset.first_seen,
        last_seen=asset.last_seen,
        endpoint_count=endpoint_count,
        card_count=card_count,
        priority_score=priority,
    )


@router.get("/assets")
def list_assets(
    params: ListParams = Depends(),
    program_id: str | None = None,
    type: str | None = None,
    scope_status: str | None = None,
    tag: str | None = None,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
) -> Page[AssetOut]:
    from sqlalchemy import func

    from ...db.models import Endpoint, ResearchCard

    stmt = select(Asset)
    if program_id:
        stmt = stmt.where(Asset.program_id == parse_uuid(program_id))
    if type:
        stmt = stmt.where(Asset.type == type)
    if scope_status:
        stmt = stmt.where(Asset.scope_status == scope_status)
    if params.q:
        like = f"%{params.q}%"
        stmt = stmt.where(or_(Asset.value_normalized.ilike(like), Asset.value_original.ilike(like)))
    order = Asset.last_seen.desc()
    rows, total = paginate(db, stmt, params.page, params.page_size, order)

    # Batch the per-asset aggregates (avoid N+1).
    asset_ids = [a.id for a in rows]
    ep_counts: dict[str, int] = {}
    card_counts: dict[str, int] = {}
    if asset_ids:
        ep_counts = dict(
            db.execute(
                select(Endpoint.asset_id, func.count())
                .where(Endpoint.asset_id.in_(asset_ids))
                .group_by(Endpoint.asset_id)
            ).all()
        )
        card_counts = dict(
            db.execute(
                select(ResearchCard.asset_id, func.count())
                .where(ResearchCard.asset_id.in_(asset_ids))
                .group_by(ResearchCard.asset_id)
            ).all()
        )

    items = [_out_batched(db, a, ep_counts.get(a.id, 0), card_counts.get(a.id, 0)) for a in rows]
    if tag:
        items = [i for i in items if tag in (i.tags or [])]
        total = len(items)
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.get("/assets/{asset_id}")
def get_asset(asset_id: str, db=Depends(get_db), user: User = Depends(get_current_user)) -> AssetOut:
    asset = db.get(Asset, parse_uuid(asset_id))
    if asset is None:
        from ...core.errors import ApiError, ErrorCode

        raise ApiError(ErrorCode.NOT_FOUND, "Asset not found", 404)
    return _out(db, asset)


@router.patch("/assets/{asset_id}")
def update_asset(
    asset_id: str,
    body: AssetUpdate,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> AssetOut:
    from ...core.errors import ApiError, ErrorCode

    asset = db.get(Asset, parse_uuid(asset_id))
    if asset is None:
        raise ApiError(ErrorCode.NOT_FOUND, "Asset not found", 404)
    if body.tags is not None:
        asset.tags = body.tags
    if body.notes is not None:
        asset.notes = body.notes
    db.commit()
    return _out(db, asset)
