"""FastAPI dependencies: DB session, current user, CSRF enforcement, rate limits."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import Settings, get_settings
from ..core.errors import ApiError, ErrorCode
from ..core.security import get_rate_limiter, verify_csrf_token
from ..db.models import Session as SessionModel
from ..db.models import User

SESSION_COOKIE = "hf_session"
CSRF_HEADER = "X-CSRF-Token"


def ensure_utc(dt: datetime) -> datetime:
    """SQLite returns naive datetimes; normalize to aware UTC for comparisons."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def get_db(request: Request) -> Session:
    factory = request.app.state.session_factory
    db: Session = factory()
    try:
        yield db
    finally:
        db.close()


def _current_session(request: Request, db: Session) -> SessionModel:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise ApiError(ErrorCode.UNAUTHORIZED, "Not authenticated", 401)
    import hashlib

    token_hash = hashlib.sha256(token.encode()).hexdigest()
    session = db.scalar(select(SessionModel).where(SessionModel.token_hash == token_hash))
    if session is None or session.revoked_at is not None:
        raise ApiError(ErrorCode.UNAUTHORIZED, "Session invalid", 401)
    if ensure_utc(session.expires_at) < datetime.now(UTC):
        raise ApiError(ErrorCode.UNAUTHORIZED, "Session expired", 401)
    return session


def get_current_session(request: Request, db: Session = Depends(get_db)) -> SessionModel:
    return _current_session(request, db)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    session = _current_session(request, db)
    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        raise ApiError(ErrorCode.UNAUTHORIZED, "Account unavailable", 401)
    request.state.session = session
    return user


def require_csrf(request: Request) -> None:
    """Verify the double-submit CSRF token for mutating requests."""
    session = getattr(request.state, "session", None)
    if session is None:
        raise ApiError(ErrorCode.UNAUTHORIZED, "Not authenticated", 401)
    presented = request.headers.get(CSRF_HEADER) or request.headers.get("x-csrf-token", "")
    if not verify_csrf_token(session.csrf_secret, presented):
        raise ApiError(ErrorCode.FORBIDDEN, "CSRF token missing or invalid", 403)


def enforce_login_rate_limit(request: Request, settings: Settings = Depends(get_settings)) -> None:
    """IP-based throttle, applied in addition to the per-account limit enforced
    inside the login handler (see auth.py)."""
    key = f"login-ip:{request.client.host if request.client else 'unknown'}"
    limiter = get_rate_limiter()
    if not limiter.allow(key, max(settings.login_rate_limit_per_minute * 10, 30), 60.0):
        raise ApiError(
            ErrorCode.RATE_LIMITED,
            "Too many login attempts from this address; try again later",
            429,
        )


def enforce_account_login_limit(username: str, settings: Settings) -> None:
    """Per-account brute-force throttle (the meaningful control, proxy-safe)."""
    key = f"login-user:{username.lower()}"
    limiter = get_rate_limiter()
    if not limiter.allow(key, settings.login_rate_limit_per_minute, 60.0):
        raise ApiError(
            ErrorCode.RATE_LIMITED,
            "Too many login attempts for this account; try again later",
            429,
        )


def csrf_token_for_current_user(request: Request, user: User = Depends(get_current_user)) -> str:
    from ..core.security import csrf_token_for

    return csrf_token_for(request.state.session.csrf_secret)


def parse_uuid(value: str) -> str:
    try:
        return str(uuid.UUID(value))
    except ValueError:
        raise ApiError(ErrorCode.VALIDATION, f"Invalid id: {value}") from None
