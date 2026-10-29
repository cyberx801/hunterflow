"""Research cards API (HF-FR-060..064)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import or_, select

from ...core.audit import AuditService
from ...core.errors import ApiError, ErrorCode
from ...db.models import (
    CardStatusHistory,
    ChecklistItem,
    ResearchCard,
    ResearchTemplate,
    User,
)
from ...schemas.inventory import (
    CardTransition,
    ChecklistItemOut,
    ResearchCardCreate,
    ResearchCardOut,
    ResearchCardUpdate,
    TemplateCreate,
    TemplateOut,
)
from ...services import research as research_service
from ..deps import get_current_user, get_db, parse_uuid, require_csrf
from ._common import ListParams, Page, paginate

router = APIRouter(tags=["research"])


def _out(db, card: ResearchCard) -> ResearchCardOut:
    items = db.scalars(
        select(ChecklistItem).where(ChecklistItem.card_id == card.id).order_by(ChecklistItem.position)
    ).all()
    return ResearchCardOut(
        id=card.id,
        program_id=card.program_id,
        asset_id=card.asset_id,
        endpoint_id=card.endpoint_id,
        title=card.title,
        hypothesis=card.hypothesis,
        test_category=card.test_category,
        required_authorization=card.required_authorization,
        required_accounts=card.required_accounts,
        methodology=card.methodology,
        status=card.status,
        observations_md=card.observations_md,
        notes_md=card.notes_md,
        next_action=card.next_action,
        priority_score=card.priority_score,
        priority_factors=card.priority_factors,
        checklist=[
            ChecklistItemOut(id=i.id, label=i.label, checked=i.checked, position=i.position)
            for i in items
        ],
        created_at=card.created_at,
        updated_at=card.updated_at,
    )


@router.get("/research")
def list_cards(
    params: ListParams = Depends(),
    program_id: str | None = None,
    status: str | None = None,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
) -> Page[ResearchCardOut]:
    stmt = select(ResearchCard)
    if program_id:
        stmt = stmt.where(ResearchCard.program_id == parse_uuid(program_id))
    if status:
        stmt = stmt.where(ResearchCard.status == status)
    if params.q:
        like = f"%{params.q}%"
        stmt = stmt.where(
            or_(ResearchCard.title.ilike(like), ResearchCard.hypothesis.ilike(like))
        )
    order = ResearchCard.priority_score.desc()
    rows, total = paginate(db, stmt, params.page, params.page_size, order)
    return Page(
        items=[_out(db, c) for c in rows], total=total, page=params.page, page_size=params.page_size
    )


@router.post("/research")
def create_card(
    body: ResearchCardCreate,
    request: Request,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> ResearchCardOut:
    if body.template_id:
        card = research_service.instantiate_template(
            db, parse_uuid(body.template_id), parse_uuid(body.program_id),
            body.title, body.asset_id, body.endpoint_id,
        )
    else:
        card = ResearchCard(
            program_id=parse_uuid(body.program_id),
            asset_id=body.asset_id,
            endpoint_id=body.endpoint_id,
            title=body.title,
            hypothesis=body.hypothesis,
            test_category=body.test_category,
            required_authorization=body.required_authorization,
            required_accounts=body.required_accounts,
            methodology=body.methodology,
            notes_md=body.notes_md,
            next_action=body.next_action,
        )
        db.add(card)
        db.flush()
        research_service.refresh_priority(db, card)
    AuditService.record(db, "research.created", "research_card", card.id, actor_id=user.id)
    db.commit()
    return _out(db, card)


@router.get("/research/{card_id}")
def get_card(card_id: str, db=Depends(get_db), user: User = Depends(get_current_user)) -> ResearchCardOut:
    return _out(db, research_service.get_card(db, parse_uuid(card_id)))


@router.patch("/research/{card_id}")
def update_card(
    card_id: str,
    body: ResearchCardUpdate,
    request: Request,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> ResearchCardOut:
    card = research_service.get_card(db, parse_uuid(card_id))
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(card, key, value)
    research_service.refresh_priority(db, card)
    db.commit()
    return _out(db, card)


@router.post("/research/{card_id}/transition")
def transition_card(
    card_id: str,
    body: CardTransition,
    request: Request,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> ResearchCardOut:
    card = research_service.get_card(db, parse_uuid(card_id))
    research_service.transition(db, card, body.to, actor_id=user.id)
    research_service.refresh_priority(db, card)
    db.commit()
    return _out(db, card)


@router.delete("/research/{card_id}")
def delete_card(
    card_id: str,
    request: Request,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> dict:
    card = research_service.get_card(db, parse_uuid(card_id))
    db.delete(card)
    AuditService.record(db, "research.deleted", "research_card", card.id, actor_id=user.id)
    db.commit()
    return {"status": "ok"}


@router.get("/research/{card_id}/history")
def card_history(card_id: str, db=Depends(get_db), user: User = Depends(get_current_user)) -> list[dict]:
    card = research_service.get_card(db, parse_uuid(card_id))
    rows = db.scalars(
        select(CardStatusHistory)
        .where(CardStatusHistory.card_id == card.id)
        .order_by(CardStatusHistory.changed_at)
    ).all()
    return [
        {"from": h.from_status, "to": h.to_status, "at": h.changed_at.isoformat()} for h in rows
    ]


@router.post("/research/{card_id}/checklist")
def add_checklist_item(
    card_id: str,
    body: dict,
    request: Request,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> ChecklistItemOut:
    card = research_service.get_card(db, parse_uuid(card_id))
    position = db.scalar(
        select(__import__("sqlalchemy").func.count())
        .select_from(ChecklistItem)
        .where(ChecklistItem.card_id == card.id)
    ) or 0
    item = ChecklistItem(card_id=card.id, label=body.get("label", ""), position=position)
    db.add(item)
    db.commit()
    return ChecklistItemOut(id=item.id, label=item.label, checked=item.checked, position=item.position)


@router.patch("/research/{card_id}/checklist/{item_id}")
def update_checklist_item(
    card_id: str,
    item_id: str,
    body: dict,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> ChecklistItemOut:
    card = research_service.get_card(db, parse_uuid(card_id))
    item = db.get(ChecklistItem, parse_uuid(item_id))
    if item is None or item.card_id != card.id:
        raise ApiError(ErrorCode.NOT_FOUND, "Checklist item not found", 404)
    if "checked" in body:
        item.checked = bool(body["checked"])
    if "label" in body:
        item.label = body["label"]
    db.commit()
    return ChecklistItemOut(id=item.id, label=item.label, checked=item.checked, position=item.position)


@router.delete("/research/{card_id}/checklist/{item_id}")
def delete_checklist_item(
    card_id: str,
    item_id: str,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> dict:
    card = research_service.get_card(db, parse_uuid(card_id))
    item = db.get(ChecklistItem, parse_uuid(item_id))
    if item is None or item.card_id != card.id:
        raise ApiError(ErrorCode.NOT_FOUND, "Checklist item not found", 404)
    db.delete(item)
    db.commit()
    return {"status": "ok"}


@router.get("/research-templates")
def list_templates(db=Depends(get_db), user: User = Depends(get_current_user)) -> list[TemplateOut]:
    templates = research_service.default_templates(db)
    return [
        TemplateOut(id=t.id, name=t.name, body=t.body or {}, created_at=t.created_at)
        for t in templates
    ]


@router.post("/research-templates")
def create_template(
    body: TemplateCreate,
    request: Request,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
) -> TemplateOut:
    t = ResearchTemplate(
        name=body.name,
        body={
            "title_pattern": body.title_pattern,
            "hypothesis": body.hypothesis,
            "test_category": body.test_category,
            "methodology": body.methodology,
            "checklist": body.checklist,
        },
    )
    db.add(t)
    db.commit()
    return TemplateOut(id=t.id, name=t.name, body=t.body or {}, created_at=t.created_at)
