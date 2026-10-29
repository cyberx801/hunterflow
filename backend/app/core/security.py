"""Authentication primitives: Argon2id password hashing, opaque session tokens,
per-session CSRF secrets, and a sliding-window rate limiter (HF-SEC-001/003/011).
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import threading
import time
from collections import deque

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

_hasher = PasswordHasher(time_cost=3, memory_cost=64 * 1024, parallelism=1)


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def new_session_token() -> tuple[str, str]:
    """Returns (plaintext_token, sha256_hash_for_storage)."""
    token = secrets.token_urlsafe(32)
    return token, hashlib.sha256(token.encode()).hexdigest()


def csrf_token_for(csrf_secret: str) -> str:
    return hmac.new(
        csrf_secret.encode(), b"hunterflow-csrf", hashlib.sha256
    ).hexdigest()


def verify_csrf_token(csrf_secret: str, presented: str) -> bool:
    if not presented:
        return False
    expected = csrf_token_for(csrf_secret)
    return hmac.compare_digest(expected, presented)


class SlidingWindowRateLimiter:
    """Thread-safe in-memory sliding window limiter (single API process).

    For the single-user deployment this is sufficient; a Redis-backed variant
    can replace it if the API ever scales horizontally.
    """

    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int, window_seconds: float) -> bool:
        now = time.monotonic()
        with self._lock:
            q = self._events.get(key)
            if q is None:
                q = deque()
                self._events[key] = q
            while q and now - q[0] > window_seconds:
                q.popleft()
            if len(q) >= limit:
                return False
            q.append(now)
            return True

    def reset(self, key: str) -> None:
        with self._lock:
            self._events.pop(key, None)


_default_limiter = SlidingWindowRateLimiter()


def get_rate_limiter() -> SlidingWindowRateLimiter:
    return _default_limiter
