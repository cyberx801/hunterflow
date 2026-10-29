"""Unit tests for pure domain modules: normalization, classification, dedup,
scoring, state machines."""

from __future__ import annotations

import pytest

from app.domain.assets.normalize import dedup_key, kind_of, normalize_host, normalize_url
from app.domain.dedup import duplicate_score
from app.domain.endpoints.classify import classify
from app.domain.scoring import score
from app.domain.state import assert_transition
from app.domain.state.machines import (
    CARD_TRANSITIONS,
    FINDING_TRANSITIONS,
    JOB_TRANSITIONS,
    TransitionError,
)


class TestNormalization:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("EXAMPLE.com", "example.com"),
            ("example.com.", "example.com"),
            ("[2001:db8::1]", "2001:db8::1"),
            ("  Api.Example.COM ", "api.example.com"),
        ],
    )
    def test_host(self, raw, expected):
        assert normalize_host(raw) == expected

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("https://Example.COM:443/path/", "https://example.com/path"),
            ("http://example.com:80", "http://example.com/"),
            ("http://example.com:8080/x", "http://example.com:8080/x"),
            ("https://example.com/a/b/#frag", "https://example.com/a/b"),
            ("HTTPS://Example.com:443/", "https://example.com/"),
        ],
    )
    def test_url(self, raw, expected):
        assert normalize_url(raw) == expected

    def test_dedup_key_equivalent_urls(self):
        a = dedup_key("url", "https://Example.com:443/a/")
        b = dedup_key("url", "https://example.com/a")
        assert a == b

    def test_dedup_key_ports_differ(self):
        assert dedup_key("url", "http://x.com:8080/") != dedup_key("url", "http://x.com:9090/")

    def test_kind_detection(self):
        assert kind_of("example.com") == "domain"
        assert kind_of("api.example.com") == "subdomain"
        assert kind_of("10.0.0.1") == "ip"
        assert kind_of("https://x.com") == "url"


class TestClassification:
    def test_auth(self):
        c = classify("POST", "/api/login")
        assert c.category == "auth"

    def test_admin(self):
        assert classify("GET", "/admin/users").category == "admin"

    def test_object_access(self):
        c = classify("GET", "/api/orders/12345")
        assert c.category == "object_access"
        assert c.is_object_access

    def test_payment(self):
        assert classify("POST", "/checkout").category == "payment"

    def test_auth_indicator_from_status(self):
        c = classify("GET", "/api/me", statuses=[200, 401])
        assert c.likely_auth_required

    def test_other_default(self):
        assert classify("GET", "/healthz").category == "other"


class TestDedup:
    def test_same_endpoint_and_title(self):
        s = duplicate_score(
            "/api/orders/1",
            "/api/orders/1",
            "object_access",
            "object_access",
            "IDOR on orders endpoint",
            "IDOR on orders endpoint",
        )
        assert s.is_duplicate

    def test_same_endpoint_pattern_similar_title(self):
        s = duplicate_score(
            "/api/orders/1",
            "/api/orders/2",
            "object_access",
            "object_access",
            "IDOR order access",
            "Broken object level authorization on order",
        )
        assert s.score >= 0.5  # candidate, maybe not full duplicate

    def test_different_everything(self):
        s = duplicate_score(
            "/a",
            "/b",
            "auth",
            "payment",
            "login bypass",
            "payment takeover",
        )
        assert not s.is_duplicate


class TestScoring:
    def test_score_zero(self):
        r = score({})
        assert r.score == 0
        assert all(not f.triggered for f in r.factors)

    def test_score_combination(self):
        r = score({"auth_sensitive": True, "untested": True, "scanner_observation": True})
        expected = 12 + 6 + 15
        assert r.score == expected

    def test_weights_override(self):
        r = score({"untested": True}, weights={"untested": 100})
        assert r.score == 100

    def test_researcher_weight_capped(self):
        r = score({}, researcher_weight=10)
        assert r.score == 20 * 3  # capped at 3x


class TestStateMachines:
    def test_card_legal(self):
        assert_transition(CARD_TRANSITIONS, "not_started", "in_progress")

    def test_card_illegal(self):
        with pytest.raises(TransitionError):
            assert_transition(CARD_TRANSITIONS, "not_started", "confirmed")

    def test_finding_legal(self):
        assert_transition(FINDING_TRANSITIONS, "under_investigation", "verified")

    def test_finding_illegal(self):
        with pytest.raises(TransitionError):
            assert_transition(FINDING_TRANSITIONS, "potential", "reported")

    def test_job_terminal_states_frozen(self):
        for status in ("completed", "cancelled"):
            assert JOB_TRANSITIONS[status] == frozenset()
