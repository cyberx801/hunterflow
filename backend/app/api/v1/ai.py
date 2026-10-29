"""AI assistant API (optional, advisory only)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ...core.config import Settings, get_settings
from ...db.models import User
from ...services import ai as ai_service
from ..deps import get_current_user, get_db, parse_uuid, require_csrf

router = APIRouter(tags=["ai"])


@router.get("/ai/status")
def ai_status(
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> dict:
    return ai_service.status(settings)


@router.post("/ai/summarize")
def summarize(
    body: dict,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_csrf),
) -> dict:
    kind = body.get("kind")
    entity_id = body.get("id")
    if not entity_id:
        from ...core.errors import ApiError, ErrorCode

        raise ApiError(ErrorCode.VALIDATION, "id is required")
    return ai_service.summarize(db, kind, parse_uuid(entity_id), settings)
