"""Deterministic duplicate detection for findings (HF-FR-083).

Linking preserves provenance; nothing is merged destructively.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_WORD_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return set(_WORD_RE.findall(text.lower()))


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


@dataclass(frozen=True)
class DuplicateScore:
    score: float
    reasons: list[str]

    @property
    def is_duplicate(self) -> bool:
        return self.score >= 0.85


def duplicate_score(
    a_endpoint: str | None,
    b_endpoint: str | None,
    a_category: str | None,
    b_category: str | None,
    a_title: str,
    b_title: str,
) -> DuplicateScore:
    """Weighted evidence:
    - same normalized endpoint: 0.45
    - same category: 0.20
    - title token overlap: 0.35
    """
    reasons: list[str] = []
    score = 0.0

    if a_endpoint and b_endpoint:
        if a_endpoint.rstrip("/").lower() == b_endpoint.rstrip("/").lower():
            score += 0.45
            reasons.append("same-endpoint")
        elif a_endpoint and b_endpoint:
            base_a = re.sub(r"/[0-9]+(/|$)", "/", a_endpoint)
            base_b = re.sub(r"/[0-9]+(/|$)", "/", b_endpoint)
            if base_a == base_b:
                score += 0.35
                reasons.append("same-endpoint-pattern")

    if a_category and b_category and a_category == b_category:
        score += 0.20
        reasons.append("same-category")

    overlap = _jaccard(_tokens(a_title), _tokens(b_title))
    score += 0.35 * overlap
    if overlap >= 0.5:
        reasons.append("title-similarity")

    return DuplicateScore(score=round(score, 4), reasons=reasons)
