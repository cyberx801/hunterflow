"""Asset & endpoint query services with explainable priority (HF-FR-110)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db.base import ensure_utc
from ..db.models import Asset, Endpoint, Finding, ResearchCard
from ..domain.scoring import score


def endpoint_priority(db: Session, endpoint: Endpoint) -> tuple[int, dict]:
    card_count = (
        db.scalar(select(func.count()).select_from(ResearchCard).where(ResearchCard.endpoint_id == endpoint.id)) or 0
    )
    finding_count = db.scalar(select(func.count()).select_from(Finding).where(Finding.endpoint_id == endpoint.id)) or 0
    now = datetime.now(UTC)
    signals = {
        "new_endpoint": endpoint.first_seen and (now - ensure_utc(endpoint.first_seen)) < timedelta(days=7),
        "auth_sensitive": bool((endpoint.auth_indicators or {}).get("auth_challenge"))
        or endpoint.category in ("auth", "account", "admin", "payment"),
        "scanner_observation": finding_count > 0,
        "untested": card_count == 0,
    }
    result = score(signals)
    return result.score, {f.key: f.triggered for f in result.factors if f.triggered}


def asset_priority(db: Session, asset: Asset) -> tuple[int, dict]:
    endpoint_count = db.scalar(select(func.count()).select_from(Endpoint).where(Endpoint.asset_id == asset.id)) or 0
    card_count = db.scalar(select(func.count()).select_from(ResearchCard).where(ResearchCard.asset_id == asset.id)) or 0
    now = datetime.now(UTC)
    signals = {
        "new_asset": (now - ensure_utc(asset.first_seen)) < timedelta(days=7),
        "untested": card_count == 0 and endpoint_count > 0,
    }
    result = score(signals)
    return result.score, {f.key: f.triggered for f in result.factors if f.triggered}


def counts_for(db: Session, program_id: str, asset_id: str) -> tuple[int, int]:
    endpoint_count = db.scalar(select(func.count()).select_from(Endpoint).where(Endpoint.asset_id == asset_id)) or 0
    card_count = db.scalar(select(func.count()).select_from(ResearchCard).where(ResearchCard.asset_id == asset_id)) or 0
    return endpoint_count, card_count
