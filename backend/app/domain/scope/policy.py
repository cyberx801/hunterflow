"""Scope policy engine - the single authority on what may be actively tested.

Pure, deterministic, zero I/O (Constitution P2/P9). Exhaustively unit-tested;
see tests/unit/test_scope_policy.py.

Matching semantics (HF-FR-005/007, security.md):
- Denies are evaluated before allows; more specific (higher priority, lower
  number) rules win within the same effect class.
- *.example.com matches a.example.com and a.b.example.com, but NOT example.com.
- A bare apex allow does not authorize its subdomains.
- CIDR rules match resolved IP addresses only (client must supply ip=).
- url_path/method/automation rules restrict an otherwise-allowed target.
- Anything not covered by an explicit allow => requires_confirmation=True
  (never silently testable).
"""

from __future__ import annotations

import ipaddress
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlsplit


class RuleKind(str, Enum):
    DOMAIN_EXACT = "domain_exact"
    DOMAIN_WILDCARD = "domain_wildcard"
    CIDR = "cidr"
    URL_PATH = "url_path"
    METHOD = "method"
    RATE_LIMIT = "rate_limit"
    AUTOMATION = "automation"


class Effect(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    RESTRICT = "restrict"


@dataclass(frozen=True)
class Rule:
    kind: RuleKind
    value: str
    effect: Effect
    priority: int = 100
    note: str | None = None

    def describe(self) -> str:
        return f"{self.effect}:{self.kind.value}:{self.value}"


@dataclass(frozen=True)
class Decision:
    allowed: bool
    requires_confirmation: bool
    matched_rules: tuple[Rule, ...] = ()
    reason: str = ""

    @property
    def blocked(self) -> bool:
        return not self.allowed


@dataclass
class Policy:
    rules: list[Rule] = field(default_factory=list)

    def with_rules(self, rules: Iterable[Rule]) -> Policy:
        return Policy(list(rules))

    # -- matching primitives -------------------------------------------------

    @staticmethod
    def _host_matches(host: str, value: str, wildcard: bool) -> bool:
        host = host.rstrip(".").lower()
        value = value.rstrip(".").lower()
        if not wildcard:
            return host == value
        # *.example.com -> matches any subdomain depth below example.com only
        if not value.startswith("*."):
            return False
        base = value[2:]
        return host.endswith("." + base) and host != base

    @staticmethod
    def _cidr_matches(ip: str | None, value: str) -> bool:
        if not ip:
            return False
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            return False
        try:
            net = ipaddress.ip_network(value, strict=False)
        except ValueError:
            return False
        return addr.version == net.version and addr in net

    # -- evaluation ----------------------------------------------------------

    def evaluate(
        self,
        host: str,
        method: str = "GET",
        path: str = "/",
        ip: str | None = None,
        automation: bool = False,
    ) -> Decision:
        host = host.rstrip(".").lower() if host else ""
        matched: list[Rule] = []
        deny_match: Rule | None = None
        allow_match: Rule | None = None

        ordered = sorted(self.rules, key=lambda r: (r.priority, r.kind.value))

        for rule in ordered:
            applies = False
            if rule.kind == RuleKind.DOMAIN_EXACT:
                applies = self._host_matches(host, rule.value, wildcard=False)
            elif rule.kind == RuleKind.DOMAIN_WILDCARD:
                applies = self._host_matches(host, rule.value, wildcard=True)
            elif rule.kind == RuleKind.CIDR:
                applies = self._cidr_matches(ip, rule.value)
            # path/method/automation rules never authorize by themselves;
            # they restrict. They only "match" when host is otherwise allowed.
            elif rule.kind == RuleKind.URL_PATH:
                applies = False
            elif rule.kind == RuleKind.METHOD:
                applies = False
            elif rule.kind == RuleKind.RATE_LIMIT:
                applies = False

            if not applies:
                continue

            if rule.effect == Effect.DENY and (deny_match is None):
                deny_match = rule
                matched.append(rule)
            elif rule.effect == Effect.ALLOW and allow_match is None:
                allow_match = rule
                matched.append(rule)

        if deny_match is not None:
            return Decision(
                allowed=False,
                requires_confirmation=False,
                matched_rules=tuple(matched),
                reason=f"denied by rule {deny_match.describe()}",
            )

        if allow_match is None:
            return Decision(
                allowed=False,
                requires_confirmation=True,
                matched_rules=tuple(matched),
                reason="no explicit allow rule covers this target; confirmation required",
            )

        # Restrictors: path, method, automation.
        restrictions: list[Rule] = []
        for rule in ordered:
            if rule.kind == RuleKind.URL_PATH:
                if self._path_applies(rule.value, path):
                    restrictions.append(rule)
            elif rule.kind == RuleKind.METHOD:
                if rule.value.upper() == method.upper():
                    restrictions.append(rule)
            elif rule.kind == RuleKind.AUTOMATION:
                restrictions.append(rule)  # value: allowed|denied|confirm

        automation_rule = next((r for r in restrictions if r.kind == RuleKind.AUTOMATION), None)
        if automation_rule is not None:
            val = automation_rule.value.lower()
            if automation and val == "denied":
                restrictions.remove(automation_rule)
                return Decision(
                    allowed=False,
                    requires_confirmation=False,
                    matched_rules=(*matched, automation_rule),
                    reason="automated testing denied for this scope",
                )
            if automation and val == "confirm":
                return Decision(
                    allowed=False,
                    requires_confirmation=True,
                    matched_rules=(*matched, automation_rule),
                    reason="automated testing requires explicit confirmation",
                )

        for r in restrictions:
            if r.effect == Effect.DENY:
                return Decision(
                    allowed=False,
                    requires_confirmation=False,
                    matched_rules=(*matched, r),
                    reason=f"restricted by rule {r.describe()}",
                )

        return Decision(
            allowed=True,
            requires_confirmation=False,
            matched_rules=tuple(matched),
            reason=f"allowed by rule {allow_match.describe()}",
        )

    @staticmethod
    def _path_applies(rule_value: str, path: str) -> bool:
        """Segment-boundary prefix semantics: '/admin' covers '/admin' and
        '/admin/x' but not '/administrator'."""
        path = path or "/"
        if rule_value.endswith("*"):
            return path.startswith(rule_value[:-1])
        if path == rule_value:
            return True
        if rule_value.endswith("/"):
            return path.startswith(rule_value)
        return path.startswith(rule_value + "/")

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def host_of_url(url: str) -> str:
        parts = urlsplit(url)
        host = parts.hostname or ""
        return host.rstrip(".").lower()

    def evaluate_url(self, url: str, method: str = "GET", ip: str | None = None) -> Decision:
        parts = urlsplit(url)
        host = (parts.hostname or "").rstrip(".").lower()
        return self.evaluate(host, method, parts.path or "/", ip=ip)

    def to_snapshot(self) -> dict:
        return {
            "rules": [
                {
                    "kind": r.kind.value,
                    "value": r.value,
                    "effect": r.effect.value,
                    "priority": r.priority,
                    "note": r.note,
                }
                for r in sorted(self.rules, key=lambda r: (r.priority, r.kind.value))
            ]
        }

    @classmethod
    def from_snapshot(cls, snapshot: dict) -> Policy:
        return cls(
            [
                Rule(
                    kind=RuleKind(item["kind"]),
                    value=item["value"],
                    effect=Effect(item["effect"]),
                    priority=item.get("priority", 100),
                    note=item.get("note"),
                )
                for item in snapshot.get("rules", [])
            ]
        )

    @classmethod
    def from_db_rules(cls, rows: Iterable) -> Policy:
        return cls(
            [
                Rule(
                    kind=RuleKind(r.kind),
                    value=r.value,
                    effect=Effect(r.effect),
                    priority=r.priority,
                    note=r.notes,
                )
                for r in rows
            ]
        )
