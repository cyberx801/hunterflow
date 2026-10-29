"""State machines: legal transitions only (HF-FR-061/081, Constitution P9)."""

from __future__ import annotations

from dataclasses import dataclass

CARD_STATUSES = [
    "not_started",
    "in_progress",
    "needs_verification",
    "confirmed",
    "rejected",
    "blocked",
    "archived",
]

CARD_TRANSITIONS: dict[str, frozenset[str]] = {
    "not_started": frozenset({"in_progress", "blocked", "archived"}),
    "in_progress": frozenset({"needs_verification", "confirmed", "rejected", "blocked", "not_started"}),
    "needs_verification": frozenset({"confirmed", "rejected", "in_progress"}),
    "confirmed": frozenset({"archived", "in_progress"}),
    "rejected": frozenset({"in_progress", "archived"}),
    "blocked": frozenset({"in_progress", "archived"}),
    "archived": frozenset({"not_started", "in_progress"}),
}

FINDING_STATUSES = [
    "potential",
    "under_investigation",
    "verified",
    "false_positive",
    "duplicate",
    "report_ready",
    "reported",
    "resolved",
]

FINDING_TRANSITIONS: dict[str, frozenset[str]] = {
    "potential": frozenset({"under_investigation", "false_positive", "duplicate"}),
    "under_investigation": frozenset({"verified", "false_positive", "duplicate", "report_ready", "potential"}),
    "verified": frozenset({"report_ready", "reported", "resolved", "false_positive", "duplicate"}),
    "false_positive": frozenset({"potential", "under_investigation"}),
    "duplicate": frozenset({"potential", "under_investigation"}),
    "report_ready": frozenset({"reported", "resolved", "under_investigation"}),
    "reported": frozenset({"resolved"}),
    "resolved": frozenset({"reported", "under_investigation"}),
}

JOB_STATUSES = ["queued", "running", "completed", "failed", "cancelled"]

JOB_TRANSITIONS: dict[str, frozenset[str]] = {
    "queued": frozenset({"running", "cancelled", "failed"}),
    "running": frozenset({"completed", "failed", "cancelled"}),
    "completed": frozenset(),
    "failed": frozenset({"queued"}),
    "cancelled": frozenset(),
}

# Verification rule (Constitution P4): only humans verify findings.
# 'verified' status requires validation_status == verified_human, enforced in services.


@dataclass(frozen=True)
class TransitionError(ValueError):
    from_status: str
    to_status: str


def assert_transition(machine: dict[str, frozenset[str]], from_status: str, to_status: str) -> None:
    allowed = machine.get(from_status)
    if allowed is None or to_status not in allowed:
        raise TransitionError(from_status=from_status, to_status=to_status)
