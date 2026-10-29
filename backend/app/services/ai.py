"""Optional AI assistant over an OpenAI-compatible API (Ollama by default).

Hard rules (project constitution P5):
- Disabled unless HF_AI_ENABLED is true. No paid API is required or configured.
- Only data that already exists in the workspace is sent; evidence file contents are
  never sent, only filenames and hashes.
- Output is advisory. It is labeled as AI-generated and must never be treated as a
  finding or as verification. The model has no tool access and cannot scan anything.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from ..core.config import Settings
from ..core.errors import ApiError, ErrorCode
from ..core.logging import get_logger
from ..core.redaction import redact_text
from ..db.models import (
    Asset,
    ChecklistItem,
    Endpoint,
    EvidenceFile,
    EvidenceLink,
    Finding,
    ResearchCard,
)

log = get_logger("hunterflow.ai")

SYSTEM_PROMPT = (
    "You are a defensive security research assistant inside a bug bounty workspace. "
    "Use ONLY the data provided by the user. Do not invent endpoints, parameters, test "
    "results, or vulnerabilities. Separate facts (what the data shows) from hypotheses "
    "(what the researcher could test next). Never claim a vulnerability is confirmed. "
    "If the data is insufficient, say what is missing. Respond in the language of the "
    "provided notes. Keep it under 220 words and use these headings: Summary, Facts, "
    "Next steps, Gaps."
)


def status(settings: Settings) -> dict:
    return {
        "enabled": settings.ai_enabled,
        "model": settings.ai_model,
        "endpoint_configured": bool(settings.ai_base_url),
        "api_key_configured": bool(settings.ai_api_key),
    }


def _evidence_metadata(db: Session, finding_id: str | None = None, card_id: str | None = None) -> list[str]:
    stmt = db.query(EvidenceLink)
    if finding_id:
        stmt = stmt.filter(EvidenceLink.finding_id == finding_id)
    elif card_id:
        stmt = stmt.filter(EvidenceLink.card_id == card_id)
    else:
        return []
    out = []
    for link in stmt.all():
        ev = db.get(EvidenceFile, link.evidence_id)
        if ev is not None:
            out.append(f"{ev.filename} (sha256 {ev.sha256[:12]}, {ev.size} bytes)")
    return out


def build_card_context(db: Session, card: ResearchCard) -> str:
    parts = [
        f"Research card: {card.title}",
        f"Status: {card.status}",
        f"Test category: {card.test_category or 'unspecified'}",
        f"Hypothesis: {card.hypothesis or 'none'}",
        f"Methodology: {card.methodology or 'none'}",
        f"Required accounts: {card.required_accounts or 'none'}",
        f"Observations: {card.observations_md or 'none'}",
        f"Notes: {card.notes_md or 'none'}",
        f"Next action: {card.next_action or 'none'}",
    ]
    items = db.query(ChecklistItem).filter(ChecklistItem.card_id == card.id).order_by(ChecklistItem.position).all()
    if items:
        parts.append("Checklist: " + "; ".join(f"{'[x]' if i.checked else '[ ]'} {i.label}" for i in items))
    if card.endpoint_id:
        ep = db.get(Endpoint, card.endpoint_id)
        if ep is not None:
            parts.append(f"Endpoint: {ep.method} {ep.path} (category {ep.category})")
    if card.asset_id:
        asset = db.get(Asset, card.asset_id)
        if asset is not None:
            parts.append(f"Asset: {asset.value_normalized} (scope {asset.scope_status})")
    evidence = _evidence_metadata(db, card_id=card.id)
    if evidence:
        parts.append("Evidence (metadata only): " + "; ".join(evidence))
    return "\n".join(parts)


def build_finding_context(db: Session, finding: Finding) -> str:
    parts = [
        f"Finding: {finding.title}",
        f"Status: {finding.status}",
        f"Validation: {finding.validation_status}",
        f"Severity: {finding.severity or 'unset'}",
        f"Confidence: {finding.confidence or 'unset'}",
        f"CWE: {finding.cwe or 'unset'}",
        f"Description: {finding.description or 'none'}",
        f"Reproduction steps: {finding.reproduction_steps or 'none'}",
        f"Impact: {finding.impact or 'none'}",
        f"Discovery source: {finding.discovery_source}",
    ]
    if finding.endpoint_id:
        ep = db.get(Endpoint, finding.endpoint_id)
        if ep is not None:
            parts.append(f"Endpoint: {ep.method} {ep.path}")
    evidence = _evidence_metadata(db, finding_id=finding.id)
    if evidence:
        parts.append("Evidence (metadata only): " + "; ".join(evidence))
    return "\n".join(parts)


def summarize(db: Session, kind: str, entity_id: str, settings: Settings) -> dict:
    if not settings.ai_enabled:
        raise ApiError(
            ErrorCode.BAD_STATE,
            "AI assistant is disabled. Set HF_AI_ENABLED=true and HF_AI_BASE_URL to an "
            "OpenAI-compatible endpoint (e.g. local Ollama).",
        )

    if kind == "research_card":
        card = db.get(ResearchCard, entity_id)
        if card is None:
            raise ApiError(ErrorCode.NOT_FOUND, "Research card not found", 404)
        source = build_card_context(db, card)
    elif kind == "finding":
        finding = db.get(Finding, entity_id)
        if finding is None:
            raise ApiError(ErrorCode.NOT_FOUND, "Finding not found", 404)
        source = build_finding_context(db, finding)
    else:
        raise ApiError(ErrorCode.VALIDATION, "kind must be research_card or finding")

    source = redact_text(source)[: settings.ai_max_input_chars]

    import httpx

    url = settings.ai_base_url.rstrip("/") + "/chat/completions"
    headers = {"Content-Type": "application/json"}
    if settings.ai_api_key:
        headers["Authorization"] = f"Bearer {settings.ai_api_key}"

    payload = {
        "model": settings.ai_model,
        "temperature": 0.2,
        "max_tokens": 700,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": source},
        ],
    }
    try:
        resp = httpx.post(url, json=payload, headers=headers, timeout=settings.ai_timeout_seconds)
    except Exception:
        log.exception("ai_request_failed", url=url)
        raise ApiError(
            ErrorCode.INTERNAL, "AI endpoint is unreachable (check HF_AI_BASE_URL)", 502
        ) from None
    if resp.status_code >= 400:
        log.info("ai_upstream_error", status=resp.status_code)
        raise ApiError(
            ErrorCode.INTERNAL,
            f"AI endpoint returned {resp.status_code}",
            502,
            details={"upstream": resp.text[:300]},
        )
    try:
        text = resp.json()["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, ValueError):
        raise ApiError(ErrorCode.INTERNAL, "AI endpoint returned an unexpected payload", 502) from None

    log.info("ai_summary_generated", kind=kind, entity_id=entity_id, chars=len(text))
    return {
        "text": text,
        "model": settings.ai_model,
        "source_chars": len(source),
        "disclaimer": (
            "AI-generated summary of workspace data. It is not a finding, not verification, "
            "and may be wrong; review it before use."
        ),
    }
