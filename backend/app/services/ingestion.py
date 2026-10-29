"""Ingestion: raw tool observations -> normalized assets/endpoints/findings.

Provenance rules (database.md):
- Raw observations are immutable and linked to their tool run.
- Normalized entities are created/updated idempotently via dedup keys.
- Scanner observations create `potential` findings only (never verified).
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.logging import get_logger
from ..db.models import (
    Asset,
    AssetObservation,
    Endpoint,
    EndpointObservation,
    Finding,
    Program,
    ScopeStatus,
)
from ..domain.assets import AssetKind, dedup_key, kind_of, normalize_host, normalize_url
from ..domain.endpoints.classify import classify
from ..domain.scope import Policy
from ..integrations.tools.base import Observation

log = get_logger("hunterflow.ingestion")


def _scope_status(policy: Policy, host: str) -> str:
    decision = policy.evaluate(host)
    if decision.allowed:
        return ScopeStatus.in_scope.value
    if decision.requires_confirmation:
        return ScopeStatus.needs_confirmation.value
    return ScopeStatus.out_of_scope.value


def _get_or_create_asset(
    db: Session,
    program: Program,
    kind: str,
    value: str,
    original: str,
    policy: Policy,
    tool_run_id: str | None,
) -> Asset:
    key_kind, key_value = dedup_key(kind, value)
    asset = db.scalar(
        select(Asset).where(
            Asset.program_id == program.id,
            Asset.type == key_kind,
            Asset.value_normalized == key_value,
        )
    )
    if asset is None:
        host = (
            normalize_host(value)
            if key_kind != AssetKind.URL
            else normalize_host(value.split("://", 1)[1].split("/", 1)[0].split(":")[0] if "://" in value else value)
        )
        asset = Asset(
            program_id=program.id,
            type=key_kind,
            value_normalized=key_value,
            value_original=original,
            scope_status=_scope_status(policy, host),
        )
        db.add(asset)
        db.flush()
    asset.last_seen = datetime.now(UTC)
    db.add(
        AssetObservation(
            program_id=program.id,
            tool_run_id=tool_run_id,
            raw={"kind": key_kind, "value": key_value},
            normalized_to=asset.id,
        )
    )
    return asset


def ingest(
    db: Session, program: Program, observation: Observation, policy: Policy, tool_run_id: str | None = None
) -> list[Asset]:
    touched: list[Asset] = []
    kind = observation.kind
    payload = observation.payload

    if kind == "subdomain":
        host = payload["host"]
        asset = _get_or_create_asset(db, program, kind_of(host), host, host, policy, tool_run_id)
        touched.append(asset)

    elif kind == "web_probe":
        url = payload["url"]
        asset = _get_or_create_asset(db, program, AssetKind.URL, normalize_url(url), url, policy, tool_run_id)
        asset.http_status = payload.get("status_code")
        asset.tech = payload.get("tech") or asset.tech
        touched.append(asset)

    elif kind == "endpoint":
        url = payload["url"]
        from urllib.parse import urlsplit

        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
        decision = policy.evaluate(host, method=payload.get("method", "GET"), path=parts.path or "/")
        if not decision.allowed:
            log.info("ingestion_blocked", url=url, reason=decision.reason)
            return touched
        asset = _get_or_create_asset(db, program, AssetKind.URL, normalize_url(url), url, policy, tool_run_id)
        method = (payload.get("method") or "GET").upper()
        path = parts.path or "/"
        endpoint = db.scalar(
            select(Endpoint).where(
                Endpoint.program_id == program.id,
                Endpoint.asset_id == asset.id,
                Endpoint.method == method,
                Endpoint.path == path,
            )
        )
        if endpoint is None:
            statuses = [payload["response_status"]] if payload.get("response_status") else []
            cls = classify(method, path, statuses=statuses)
            endpoint = Endpoint(
                program_id=program.id,
                asset_id=asset.id,
                method=method,
                path=path,
                query_params={"_": 1} if parts.query else None,
                content_types=[payload["content_type"]] if payload.get("content_type") else None,
                auth_indicators={"auth_challenge": cls.likely_auth_required},
                category=cls.category,
                status_distribution={str(payload["response_status"]): 1} if payload.get("response_status") else None,
            )
            db.add(endpoint)
            db.flush()
        endpoint.last_seen = datetime.now(UTC)
        db.add(EndpointObservation(endpoint_id=endpoint.id, tool_run_id=tool_run_id, raw=payload))
        touched.append(asset)

    elif kind == "scanner_finding":
        existing = db.scalar(
            select(Finding).where(
                Finding.program_id == program.id,
                Finding.discovery_source == "tool_observation",
                Finding.source_ref == f"{tool_run_id}:{payload.get('template_id')}:{payload.get('matched_at')}",
            )
        )
        if existing is None:
            db.add(
                Finding(
                    program_id=program.id,
                    title=payload.get("name") or payload.get("template_id") or "Scanner observation",
                    description=f"Template: {payload.get('template_id')}",
                    severity=payload.get("severity"),
                    status="potential",
                    validation_status="unverified",
                    discovery_source="tool_observation",
                    source_ref=f"{tool_run_id}:{payload.get('template_id')}:{payload.get('matched_at')}",
                )
            )
    return touched
