"""Exhaustive scope policy engine tests (T-021)."""

from __future__ import annotations

import pytest

from app.domain.scope import Effect, Policy, Rule, RuleKind


def policy(*rules: Rule) -> Policy:
    return Policy(list(rules))


EXACT = Rule(RuleKind.DOMAIN_EXACT, "example.com", Effect.ALLOW, priority=10)
WILD = Rule(RuleKind.DOMAIN_WILDCARD, "*.example.com", Effect.ALLOW, priority=20)


class TestDomainMatching:
    def test_exact_match(self):
        d = policy(EXACT).evaluate("example.com")
        assert d.allowed and not d.requires_confirmation

    def test_exact_no_subdomain_leak(self):
        d = policy(EXACT).evaluate("api.example.com")
        assert not d.allowed and d.requires_confirmation

    def test_wildcard_matches_subdomains(self):
        d = policy(WILD).evaluate("api.example.com")
        assert d.allowed

    def test_wildcard_deep_subdomain(self):
        d = policy(WILD).evaluate("a.b.c.example.com")
        assert d.allowed

    def test_wildcard_not_apex(self):
        d = policy(WILD).evaluate("example.com")
        assert not d.allowed and d.requires_confirmation

    def test_wildcard_not_other_domain(self):
        d = policy(WILD).evaluate("example.net")
        assert not d.allowed and d.requires_confirmation

    def test_wildcard_not_suffix_trick(self):
        d = policy(WILD).evaluate("notexample.com")
        assert not d.allowed and d.requires_confirmation

    def test_trailing_dot_normalized(self):
        d = policy(EXACT).evaluate("example.com.")
        assert d.allowed

    def test_case_insensitive(self):
        d = policy(EXACT).evaluate("EXAMPLE.com")
        assert d.allowed

    def test_unknown_target_requires_confirmation(self):
        d = policy(EXACT).evaluate("other.org")
        assert not d.allowed
        assert d.requires_confirmation


class TestDenyPrecedence:
    def test_deny_beats_allow(self):
        p = policy(
            EXACT,
            Rule(RuleKind.DOMAIN_EXACT, "example.com", Effect.DENY, priority=5),
        )
        d = p.evaluate("example.com")
        assert not d.allowed
        assert not d.requires_confirmation

    def test_specific_deny_inside_wildcard(self):
        p = policy(
            WILD,
            Rule(RuleKind.DOMAIN_EXACT, "staging.example.com", Effect.DENY, priority=5),
        )
        assert p.evaluate("api.example.com").allowed
        d = p.evaluate("staging.example.com")
        assert not d.allowed and not d.requires_confirmation

    def test_wildcard_deny_beats_exact_allow(self):
        p = policy(
            Rule(RuleKind.DOMAIN_EXACT, "example.com", Effect.ALLOW, priority=10),
            Rule(RuleKind.DOMAIN_WILDCARD, "*.example.com", Effect.DENY, priority=5),
        )
        assert p.evaluate("api.example.com").blocked
        assert p.evaluate("example.com").allowed


class TestCidr:
    def test_cidr_ip_match(self):
        p = policy(Rule(RuleKind.CIDR, "10.0.0.0/24", Effect.ALLOW))
        assert p.evaluate("host.internal", ip="10.0.0.5").allowed

    def test_cidr_ip_miss(self):
        p = policy(Rule(RuleKind.CIDR, "10.0.0.0/24", Effect.ALLOW))
        d = p.evaluate("host.internal", ip="10.0.1.5")
        assert not d.allowed and d.requires_confirmation

    def test_cidr_does_not_authorize_host_without_ip(self):
        p = policy(Rule(RuleKind.CIDR, "10.0.0.0/24", Effect.ALLOW))
        d = p.evaluate("host.internal")
        assert not d.allowed and d.requires_confirmation

    def test_ipv6_cidr(self):
        p = policy(Rule(RuleKind.CIDR, "2001:db8::/32", Effect.ALLOW))
        assert p.evaluate("h", ip="2001:db8::1").allowed
        assert p.evaluate("h", ip="2001:db9::1").blocked


class TestRestrictors:
    def test_path_deny(self):
        p = policy(EXACT, Rule(RuleKind.URL_PATH, "/admin", Effect.DENY, priority=5))
        assert p.evaluate("example.com", path="/home").allowed
        d = p.evaluate("example.com", path="/admin")
        assert not d.allowed and not d.requires_confirmation

    def test_path_wildcard(self):
        p = policy(EXACT, Rule(RuleKind.URL_PATH, "/api/*", Effect.DENY, priority=5))
        assert p.evaluate("example.com", path="/api/v1/users").blocked
        assert p.evaluate("example.com", path="/apix").allowed

    def test_method_deny(self):
        p = policy(EXACT, Rule(RuleKind.METHOD, "POST", Effect.DENY, priority=5))
        assert p.evaluate("example.com", method="GET").allowed
        assert p.evaluate("example.com", method="POST").blocked

    def test_automation_denied(self):
        p = policy(EXACT, Rule(RuleKind.AUTOMATION, "denied", Effect.RESTRICT))
        d = p.evaluate("example.com", automation=True)
        assert not d.allowed and not d.requires_confirmation

    def test_automation_confirm(self):
        p = policy(EXACT, Rule(RuleKind.AUTOMATION, "confirm", Effect.RESTRICT))
        d = p.evaluate("example.com", automation=True)
        assert not d.allowed and d.requires_confirmation

    def test_automation_allowed(self):
        p = policy(EXACT, Rule(RuleKind.AUTOMATION, "allowed", Effect.RESTRICT))
        assert p.evaluate("example.com", automation=True).allowed


class TestUrlEvaluation:
    def test_url_host_and_path(self):
        p = policy(EXACT, Rule(RuleKind.URL_PATH, "/admin", Effect.DENY, priority=5))
        assert p.evaluate_url("https://example.com/home").allowed
        assert p.evaluate_url("https://example.com/admin/x").blocked

    def test_url_port_ignored(self):
        p = policy(EXACT)
        assert p.evaluate_url("https://example.com:8443/x").allowed

    def test_snapshot_roundtrip(self):
        p = policy(EXACT, WILD)
        snap = p.to_snapshot()
        restored = Policy.from_snapshot(snap)
        assert restored.evaluate("example.com").allowed
        assert restored.evaluate("api.example.com").allowed
        assert restored.evaluate("other.org").requires_confirmation


@pytest.mark.parametrize(
    "host",
    [
        "127.0.0.1",
        "localhost",
        "169.254.169.254",
        "internal.corp",
        "evil.example.com.evil.net",
    ],
)
def test_never_allowed_without_rule(host):
    assert policy().evaluate(host).blocked
    assert policy().evaluate(host).requires_confirmation
