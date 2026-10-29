"""User management for a shared team workspace (admin only).

v0.4 is a *team workspace*: every authenticated user sees the same programs and
data. There is no per-user isolation yet. The first account is the administrator;
`HF_ALLOW_REGISTRATION=true` lets people self-register as members. Admins can
create, deactivate, promote and demote users.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from ...core.audit import AuditService
from ...core.errors import ApiError, ErrorCode
from ...core.security import hash_password
from ...db.models import Session as SessionModel
from ...db.models import User
from ..deps import get_db, parse_uuid, require_admin, require_csrf

router = APIRouter(tags=["users"])


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=12, max_length=128)
    is_admin: bool = False


class UserUpdate(BaseModel):
    is_active: bool | None = None
    is_admin: bool | None = None


class PasswordReset(BaseModel):
    password: str = Field(min_length=12, max_length=128)


def _out(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "is_admin": user.is_admin,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat(),
    }


def _admin_count(db) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(User)
            .where(User.is_admin.is_(True), User.is_active.is_(True))
        )
        or 0
    )


@router.get("/users")
def list_users(db=Depends(get_db), admin: User = Depends(require_admin)) -> list[dict]:
    rows = db.scalars(select(User).order_by(User.created_at)).all()
    return [_out(u) for u in rows]


@router.post("/users", status_code=201)
def create_user(
    body: UserCreate,
    request: Request,
    db=Depends(get_db),
    admin: User = Depends(require_admin),
    _: None = Depends(require_csrf),
) -> dict:
    if db.scalar(select(User).where(User.username == body.username)) is not None:
        raise ApiError(ErrorCode.CONFLICT, "Username already exists", 409)
    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        is_admin=body.is_admin,
    )
    db.add(user)
    db.flush()
    AuditService.record(
        db, "user.created", "user", user.id,
        after={"username": user.username, "is_admin": user.is_admin},
        actor_id=admin.id, ip=request.client.host if request.client else None,
    )
    db.commit()
    return _out(user)


@router.patch("/users/{user_id}")
def update_user(
    user_id: str,
    body: UserUpdate,
    request: Request,
    db=Depends(get_db),
    admin: User = Depends(require_admin),
    _: None = Depends(require_csrf),
) -> dict:
    user = db.get(User, parse_uuid(user_id))
    if user is None:
        raise ApiError(ErrorCode.NOT_FOUND, "User not found", 404)

    if user.id == admin.id and body.is_active is False:
        raise ApiError(ErrorCode.BAD_STATE, "You cannot deactivate your own account")
    if user.id == admin.id and body.is_admin is False and _admin_count(db) <= 1:
        raise ApiError(ErrorCode.BAD_STATE, "Cannot remove the last administrator")
    if body.is_active is False and user.is_admin and _admin_count(db) <= 1:
        raise ApiError(ErrorCode.BAD_STATE, "Cannot deactivate the last administrator")

    if body.is_active is not None:
        user.is_active = body.is_active
        if not body.is_active:
            db.query(SessionModel).filter(SessionModel.user_id == user.id).delete()
    if body.is_admin is not None:
        user.is_admin = body.is_admin

    AuditService.record(
        db, "user.updated", "user", user.id,
        after={"is_active": user.is_active, "is_admin": user.is_admin},
        actor_id=admin.id, ip=request.client.host if request.client else None,
    )
    db.commit()
    return _out(user)


@router.post("/users/{user_id}/reset-password")
def reset_password(
    user_id: str,
    body: PasswordReset,
    request: Request,
    db=Depends(get_db),
    admin: User = Depends(require_admin),
    _: None = Depends(require_csrf),
) -> dict:
    user = db.get(User, parse_uuid(user_id))
    if user is None:
        raise ApiError(ErrorCode.NOT_FOUND, "User not found", 404)
    user.password_hash = hash_password(body.password)
    db.query(SessionModel).filter(SessionModel.user_id == user.id).delete()
    AuditService.record(
        db, "user.password_reset", "user", user.id, actor_id=admin.id,
        ip=request.client.host if request.client else None,
    )
    db.commit()
    return {"status": "ok"}
