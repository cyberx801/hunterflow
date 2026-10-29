"""Endpoint classification and auth-indicator heuristics (HF-FR-050/051).

Informational only: a category never implies a vulnerability (Constitution P5).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

CATEGORIES = [
    "auth",
    "account",
    "profile",
    "admin",
    "file",
    "payment",
    "object_access",
    "resource_mgmt",
    "api_versioning",
    "other",
]

_SEGMENT_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(^|/)(login|signin|sign-in|sign_in|logout|signout|sign-up|signup|register|auth|oauth|token|session)(/|$)"), "auth"),
    (re.compile(r"(^|/)(admin|administrator|manage|console|internal|dashboard)(/|$)"), "admin"),
    (re.compile(r"(^|/)(account|settings|preferences|profile|user|me)(/|$)"), "account"),
    (re.compile(r"(^|/)(upload|download|file|files|image|images|attachment|static|media|export|import)(/|$)"), "file"),
    (re.compile(r"(^|/)(pay|payment|billing|checkout|invoice|subscription|order)(/|$)"), "payment"),
    (re.compile(r"(^|/)(api/v\d+|v\d+|graphql|swagger|openapi)(/|$)"), "api_versioning"),
]

_OBJECT_ACCESS = re.compile(r"/(?:users?|orders?|items?|invoices?|documents?|projects?|organizations?|customers?|tickets?)/[^/?#]+/?$")


def _has_identifier_segment(path: str) -> bool:
    """A trailing dynamic identifier segment suggests object-level access."""
    tail = path.rstrip("/").split("/")[-1]
    return bool(re.fullmatch(r"[0-9]+", tail)) or (
        len(tail) > 16 and not tail.startswith(".")
    )


@dataclass(frozen=True)
class Classification:
    category: str
    is_object_access: bool = False
    likely_auth_required: bool = False
    confidence: float = 0.0
    hints: list[str] = field(default_factory=list)


def classify(method: str, path: str, statuses: list[int] | None = None) -> Classification:
    p = path or "/"
    hints: list[str] = []
    category = "other"

    if _OBJECT_ACCESS.search(p):
        category = "object_access"
        hints.append("identifier-in-path")

    for pattern, cat in _SEGMENT_RULES:
        if pattern.search(p):
            category = cat
            hints.append(cat)
            break

    is_object = bool(_OBJECT_ACCESS.search(p)) and category in ("object_access", "other")
    statuses = statuses or []
    likely_auth = any(s in (401, 403) for s in statuses)
    if likely_auth:
        hints.append("auth-challenge-observed")

    confidence = 0.0
    if hints:
        confidence = 0.6 + 0.15 * min(len(hints) - 1, 2)

    return Classification(
        category=category,
        is_object_access=is_object,
        likely_auth_required=likely_auth,
        confidence=confidence,
        hints=hints,
    )
