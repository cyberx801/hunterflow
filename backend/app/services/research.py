"""Research cards: state machine transitions, scoring, templates (HF-FR-060..064)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.audit import AuditService
from ..core.errors import ApiError, ErrorCode
from ..db.models import (
    CardStatus,
    CardStatusHistory,
    ChecklistItem,
    ResearchCard,
    ResearchTemplate,
)
from ..domain.state import CARD_TRANSITIONS, TransitionError, assert_transition


def get_card(db: Session, card_id: str) -> ResearchCard:
    card = db.get(ResearchCard, card_id)
    if card is None:
        raise ApiError(ErrorCode.NOT_FOUND, "Research card not found", 404)
    return card


def transition(db: Session, card: ResearchCard, to: str, actor_id: str | None = None) -> ResearchCard:
    try:
        assert_transition(CARD_TRANSITIONS, card.status, to)
    except TransitionError:
        raise ApiError(
            ErrorCode.BAD_STATE,
            f"Invalid transition: {card.status} -> {to}",
        ) from None
    db.add(
        CardStatusHistory(
            card_id=card.id,
            from_status=card.status,
            to_status=to,
            changed_by=actor_id,
        )
    )
    card.status = to
    db.flush()
    AuditService.record(
        db,
        "research.transition",
        "research_card",
        card.id,
        before={"status": card.status, "from": card.status},
        after={"status": to},
        actor_id=actor_id,
    )
    return card


def refresh_priority(db: Session, card: ResearchCard) -> None:
    """Deterministic scoring for cards; stored so the board can sort (HF-FR-110)."""
    from ..domain.scoring import score

    signals = {
        "untested": card.status in ("not_started", "in_progress"),
        "auth_sensitive": False,
    }
    if card.endpoint_id:
        from ..db.models import Endpoint

        endpoint = db.get(Endpoint, card.endpoint_id)
        if endpoint is not None:
            signals["auth_sensitive"] = bool(
                (endpoint.auth_indicators or {}).get("auth_challenge")
            ) or endpoint.category in ("auth", "account", "admin", "payment")
            if card.status == "confirmed":
                signals = {**signals, "untested": False}
    result = score(signals, researcher_weight=1 if card.status in ("needs_verification", "confirmed") else 0)
    card.priority_score = result.score
    card.priority_factors = {f.key: f.triggered for f in result.factors}


def instantiate_template(
    db: Session, template_id: str, program_id: str, title: str, asset_id: str | None, endpoint_id: str | None
) -> ResearchCard:
    template = db.get(ResearchTemplate, template_id)
    if template is None:
        raise ApiError(ErrorCode.NOT_FOUND, "Template not found", 404)
    body = template.body or {}
    card = ResearchCard(
        program_id=program_id,
        asset_id=asset_id,
        endpoint_id=endpoint_id,
        title=(body.get("title_pattern") or "{}").replace("{title}", title)
        if title
        else body.get("title_pattern") or "Untitled research card",
        hypothesis=body.get("hypothesis"),
        test_category=body.get("test_category"),
        methodology=body.get("methodology"),
        status=CardStatus.not_started.value,
    )
    db.add(card)
    db.flush()
    for position, label in enumerate(body.get("checklist") or []):
        db.add(ChecklistItem(card_id=card.id, label=label, position=position))
    refresh_priority(db, card)
    db.flush()
    return card


def default_templates(db: Session) -> list[ResearchTemplate]:
    """Seed built-in templates on first access (idempotent)."""
    builtins = [
        {
            "name": "BOLA / IDOR — object-level authorization",
            "title_pattern": "BOLA check: {title}",
            "hypothesis": "Verify whether object-level authorization is enforced between two authorized test accounts.",
            "test_category": "object_access",
            "methodology": "1) Access resource as account A. 2) Repeat as account B using A's resource identifier. 3) Compare responses and record observations.",
            "checklist": [
                "Identify resource identifiers",
                "Prepare two authorized accounts",
                "Repeat request as second account",
                "Compare responses",
                "Record evidence",
                "State verdict with evidence",
            ],
        },
        {
            "name": "Authn bypass — missing or weak authentication",
            "title_pattern": "Authn review: {title}",
            "hypothesis": "Determine whether the endpoint enforces authentication for all methods and roles.",
            "test_category": "auth",
            "methodology": "Probe endpoint without credentials, with role A, with role B; note 401/403 behavior per method.",
            "checklist": ["Unauthenticated probe", "Role A probe", "Role B probe", "Document status codes", "Verdict"],
        },
        {
            "name": "IDOR via parameter tampering",
            "title_pattern": "Param tamper: {title}",
            "hypothesis": "Test whether user-controlled identifiers are validated against the session's ownership.",
            "test_category": "object_access",
            "methodology": "Enumerate parameters holding identifiers; substitute other users' identifiers; compare responses.",
            "checklist": [
                "Map identifier parameters",
                "Collect second account identifiers",
                "Substitute identifiers",
                "Compare responses",
                "Verdict",
            ],
        },
    ]
    existing = db.scalars(
        select(ResearchTemplate).where(ResearchTemplate.name.in_([b["name"] for b in builtins]))
    ).all()
    names = {t.name for t in existing}
    created = []
    for b in builtins:
        if b["name"] in names:
            continue
        t = ResearchTemplate(name=b["name"], body=b)
        db.add(t)
        created.append(t)
    if created:
        db.commit()
    return list(existing) + created
