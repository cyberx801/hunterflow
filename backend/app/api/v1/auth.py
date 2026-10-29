"""Authentication endpoints: first-run registration, login/logout, sessions, CSRF.

Session cookie: HttpOnly, SameSite=Lax, Secure in production (HF-SEC-002).
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from ...core.config import Settings, get_settings
from ...core.errors import ApiError, ErrorCode
from ...core.security import (
    csrf_token_for,
    hash_password,
    new_session_token,
    verify_password,
)
from ...db.models import Session, User
from ..deps import (
    SESSION_COOKIE,
    enforce_account_login_limit,
    enforce_login_rate_limit,
    ensure_utc,
    get_current_user,
    get_db,
    parse_uuid,
    require_csrf,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=12, max_length=128)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=12, max_length=128)


def _issue_session(db, user: User, settings: Settings, response: Response) -> Session:
    token, token_hash = new_session_token()
    csrf_secret = secrets.token_urlsafe(32)
    session = Session(
        user_id=user.id,
        token_hash=token_hash,
        csrf_secret=csrf_secret,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.session_ttl_days),
    )
    db.add(session)
    db.flush()
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.session_ttl_days * 86400,
        path="/",
    )
    return session


def _user_payload(user: User, session: Session) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "csrf_token": csrf_token_for(session.csrf_secret),
        "expires_at": session.expires_at.isoformat(),
    }


@router.get("/bootstrap")
def bootstrap_status(db=Depends(get_db)) -> dict:
    user_count = db.scalar(select(func.count()).select_from(User)) or 0
    return {"setup_required": user_count == 0}


@router.post("/register")
def register(
    body: RegisterRequest,
    request: Request,
    response: Response,
    db=Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    user_count = db.scalar(select(func.count()).select_from(User)) or 0
    if user_count > 0:
        raise ApiError(ErrorCode.FORBIDDEN, "Registration disabled: an account already exists", 403)
    if settings.bootstrap_username and settings.bootstrap_password:
        # Bootstrap account takes precedence; registration is locked.
        raise ApiError(ErrorCode.FORBIDDEN, "Registration disabled", 403)
    user = User(username=body.username, password_hash=hash_password(body.password))
    db.add(user)
    db.flush()
    session = _issue_session(db, user, settings, response)
    db.commit()
    return _user_payload(user, session)


@router.post("/login", dependencies=[Depends(enforce_login_rate_limit)])
def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db=Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    enforce_account_login_limit(body.username, settings)
    user = db.scalar(select(User).where(User.username == body.username))
    if user is None or not verify_password(body.password, user.password_hash):
        raise ApiError(ErrorCode.UNAUTHORIZED, "Invalid credentials", 401)
    if not user.is_active:
        raise ApiError(ErrorCode.UNAUTHORIZED, "Account disabled", 401)
    session = _issue_session(db, user, settings, response)
    db.commit()
    return _user_payload(user, session)


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
):
    session = request.state.session
    session.revoked_at = datetime.now(timezone.utc)
    db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"status": "ok"}


@router.get("/me")
def me(request: Request, user: User = Depends(get_current_user)) -> dict:
    return _user_payload(user, request.state.session)


@router.get("/sessions")
def list_sessions(
    request: Request, db=Depends(get_db), user: User = Depends(get_current_user)
) -> dict:
    now = datetime.now(timezone.utc)
    rows = db.scalars(
        select(Session).where(Session.user_id == user.id).order_by(Session.created_at.desc())
    ).all()
    current_id = request.state.session.id
    return {
        "items": [
            {
                "id": s.id,
                "current": s.id == current_id,
                "created_at": s.created_at.isoformat(),
                "expires_at": s.expires_at.isoformat(),
                "revoked": s.revoked_at is not None or ensure_utc(s.expires_at) < now,
            }
            for s in rows
        ]
    }


@router.post("/sessions/{session_id}/revoke")
def revoke_session(
    session_id: str,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
):
    sid = parse_uuid(session_id)
    session = db.get(Session, sid)
    if session is None or session.user_id != user.id:
        raise ApiError(ErrorCode.NOT_FOUND, "Session not found", 404)
    session.revoked_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "ok"}


@router.post("/change-password")
def change_password(
    body: ChangePasswordRequest,
    db=Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(require_csrf),
):
    if not verify_password(body.current_password, user.password_hash):
        raise ApiError(ErrorCode.FORBIDDEN, "Current password incorrect", 403)
    user.password_hash = hash_password(body.new_password)
    db.commit()
    return {"status": "ok"}
