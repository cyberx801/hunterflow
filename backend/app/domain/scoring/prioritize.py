"""Deterministic, explainable research prioritization (HF-FR-110/111/112).

The score is a lead indicator: it ranks research opportunities. It is NEVER a
vulnerability claim. Every factor is returned for display.
"""

from __future__ import annotations

from dataclasses import dataclass, field

DEFAULT_WEIGHTS: dict[str, int] = {
    "new_asset": 10,
    "new_endpoint": 8,
    "auth_sensitive": 12,
    "unusual_response": 10,
    "scanner_observation": 15,
    "untested": 6,
    "recent_change": 8,
    "researcher_weight": 20,
}

FACTOR_LABELS: dict[str, str] = {
    "new_asset": "Newly discovered asset",
    "new_endpoint": "Newly discovered endpoint",
    "auth_sensitive": "Authentication-sensitive operation",
    "unusual_response": "Unusual response behavior",
    "scanner_observation": "Relevant scanner observation",
    "untested": "Previously untested",
    "recent_change": "Recent asset change",
    "researcher_weight": "Researcher-defined importance",
}


@dataclass(frozen=True)
class Factor:
    key: str
    label: str
    weight: int
    triggered: bool


@dataclass(frozen=True)
class PriorityResult:
    score: int
    factors: list[Factor]


def score(
    signals: dict[str, bool],
    weights: dict[str, int] | None = None,
    researcher_weight: int = 0,
) -> PriorityResult:
    effective = {**DEFAULT_WEIGHTS, **(weights or {})}
    total = 0
    factors: list[Factor] = []
    for key in DEFAULT_WEIGHTS:
        w = int(effective.get(key, DEFAULT_WEIGHTS[key]))
        if key == "researcher_weight":
            triggered = researcher_weight > 0
            value = w * min(researcher_weight, 3)
        else:
            triggered = bool(signals.get(key, False))
            value = w if triggered else 0
        total += value
        factors.append(
            Factor(key=key, label=FACTOR_LABELS[key], weight=w, triggered=triggered)
        )
    return PriorityResult(score=total, factors=factors)
