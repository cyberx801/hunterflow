"""HTTP comparison engine (HF-FR-073/074/075).

Pure and deterministic: header normalization, dynamic-value masking, and a
line-based body diff. A status-code-only difference produces review_required,
never an automatic vulnerability conclusion.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from typing import Any

DEFAULT_IGNORE_HEADERS = [
    "date",
    "set-cookie",
    "expires",
    "last-modified",
    "etag",
    "server",
    "x-request-id",
    "x-correlation-id",
    "x-trace-id",
    "x-amz-request-id",
    "cf-ray",
    "x-ratelimit-remaining",
]

DEFAULT_DYNAMIC_RULES: list[dict[str, str]] = [
    {"name": "uuid", "pattern": r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"},
    {"name": "timestamp-ms", "pattern": r"\b1[0-9]{12}\b"},
    {"name": "timestamp-s", "pattern": r"\b1[0-9]{9}\b"},
    {"name": "iso-datetime", "pattern": r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z?"},
    {"name": "jwt", "pattern": r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}"},
    {"name": "hex-token", "pattern": r"\b[0-9a-f]{32,}\b"},
]


@dataclass
class NormalizationProfile:
    ignore_headers: list[str] = field(default_factory=lambda: list(DEFAULT_IGNORE_HEADERS))
    dynamic_rules: list[dict[str, str]] = field(default_factory=lambda: list(DEFAULT_DYNAMIC_RULES))
    ignore_headers_custom: list[str] = field(default_factory=list)

    @property
    def ignored(self) -> set[str]:
        return {h.lower() for h in [*self.ignore_headers, *self.ignore_headers_custom]}

    def mask(self, text: str) -> str:
        out = text
        for rule in self.dynamic_rules:
            out = re.sub(rule["pattern"], f"[{rule['name']}]", out)
        return out

    def normalize_headers(self, headers: dict[str, Any] | None) -> dict[str, str]:
        result: dict[str, str] = {}
        for key, value in (headers or {}).items():
            if str(key).lower() in self.ignored:
                continue
            result[key] = self.mask(str(value))
        return result

    def normalize_body(self, body: str | None) -> str:
        return self.mask(body or "")


@dataclass
class Pane:
    label: str
    method: str
    url: str
    request_headers: dict[str, str]
    request_body: str
    status: int | None
    response_headers: dict[str, str]
    response_body: str
    timing: dict | None


@dataclass
class DiffLine:
    kind: str  # same | added | removed | header-diff
    left: str | None
    right: str | None


@dataclass
class ComparisonResult:
    panes: list[Pane]
    body_diff: list[DiffLine]
    header_diff: dict[str, tuple[str | None, str | None]]  # header name -> (left, right) normalized
    status_diff: bool
    review_required: bool
    review_reason: str | None = None


def build_panes(transactions: list[dict], profile: NormalizationProfile) -> list[Pane]:
    panes = []
    for tx in transactions:
        panes.append(
            Pane(
                label=tx.get("account_tag") or tx.get("id", "")[:8],
                method=tx.get("method", ""),
                url=tx.get("url", ""),
                request_headers=profile.normalize_headers(tx.get("request_headers")),
                request_body=profile.normalize_body(tx.get("request_body")),
                status=tx.get("response_status"),
                response_headers=profile.normalize_headers(tx.get("response_headers")),
                response_body=profile.normalize_body(tx.get("response_body")),
                timing=tx.get("timing"),
            )
        )
    return panes


def compare(transactions: list[dict], profile: NormalizationProfile | None = None) -> ComparisonResult:
    profile = profile or NormalizationProfile()
    if len(transactions) < 2:
        raise ValueError("Comparison requires at least two transactions")
    panes = build_panes(transactions, profile)

    # Headers diff across the first two panes (pairwise MVP; N panes rendered side-by-side).
    header_diff: dict[str, tuple[str | None, str | None]] = {}
    left, right = panes[0], panes[-1]
    all_headers = sorted(set(left.response_headers) | set(right.response_headers))
    for name in all_headers:
        lv = left.response_headers.get(name)
        rv = right.response_headers.get(name)
        if lv != rv:
            header_diff[name] = (lv, rv)

    status_diff = left.status != right.status

    body_diff: list[DiffLine] = []
    for line in difflib.unified_diff(
        left.response_body.splitlines(),
        right.response_body.splitlines(),
        lineterm="",
        n=2,
    ):
        if line.startswith("---") or line.startswith("+++") or line.startswith("@@"):
            continue
        if line.startswith("-"):
            body_diff.append(DiffLine(kind="removed", left=line[1:], right=None))
        elif line.startswith("+"):
            body_diff.append(DiffLine(kind="added", left=None, right=line[1:]))
        else:
            body_diff.append(DiffLine(kind="same", left=line[1:], right=line[1:]))

    review_required = status_diff and not body_diff and not header_diff
    reason = (
        "Status codes differ but normalized bodies and headers are identical — "
        "review required; this alone does not indicate a vulnerability (HF-FR-075)."
        if review_required
        else None
    )

    return ComparisonResult(
        panes=panes,
        body_diff=body_diff,
        header_diff=header_diff,
        status_diff=status_diff,
        review_required=review_required,
        review_reason=reason,
    )
