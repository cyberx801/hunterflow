"""End-to-end API workflow tests: research, traffic, findings, evidence, reports."""

from __future__ import annotations

import hashlib
import io
import json

from tests.helpers import csrf_headers, register_user


def _program(client, csrf, name="ACME"):
    r = client.post("/api/v1/programs", json={"name": name, "platform": "other"}, headers=csrf_headers(csrf))
    assert r.status_code == 200
    return r.json()


def _rule(client, csrf, pid, value="*.example.com"):
    r = client.post(
        f"/api/v1/programs/{pid}/scope/rules",
        json={"kind": "domain_wildcard", "value": value, "effect": "allow", "priority": 10},
        headers=csrf_headers(csrf),
    )
    assert r.status_code == 200
    return r.json()


class TestResearchWorkflow:
    def test_card_lifecycle_with_template(self, client):
        me = register_user(client)
        csrf = me["csrf_token"]
        pid = _program(client, csrf)["id"]

        templates = client.get("/api/v1/research-templates").json()
        assert len(templates) >= 3  # built-in templates seeded

        r = client.post(
            "/api/v1/research",
            json={
                "program_id": pid,
                "template_id": templates[0]["id"],
                "title": "orders endpoint",
            },
            headers=csrf_headers(csrf),
        )
        assert r.status_code == 200, r.text
        card = r.json()
        assert card["status"] == "not_started"
        assert len(card["checklist"]) == 6
        assert card["hypothesis"]  # from template

        # Legal transition
        r = client.post(
            f"/api/v1/research/{card['id']}/transition",
            json={"to": "in_progress"},
            headers=csrf_headers(csrf),
        )
        assert r.status_code == 200
        assert r.json()["status"] == "in_progress"

        # Illegal transition rejected
        r = client.post(
            f"/api/v1/research/{card['id']}/transition",
            json={"to": "reported"},
            headers=csrf_headers(csrf),
        )
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "BAD_STATE"

        # History preserved
        history = client.get(f"/api/v1/research/{card['id']}/history").json()
        assert len(history) == 1
        assert history[0]["to"] == "in_progress"

        # Checklist toggle
        item = card["checklist"][0]
        r = client.patch(
            f"/api/v1/research/{card['id']}/checklist/{item['id']}",
            json={"checked": True},
            headers=csrf_headers(csrf),
        )
        assert r.status_code == 200
        assert r.json()["checked"] is True

    def test_card_priority_factors(self, client):
        me = register_user(client)
        csrf = me["csrf_token"]
        pid = _program(client, csrf)["id"]
        r = client.post(
            "/api/v1/research",
            json={"program_id": pid, "title": "Manual card"},
            headers=csrf_headers(csrf),
        )
        card = r.json()
        assert card["priority_score"] >= 0
        assert isinstance(card["priority_factors"], dict)
        assert "untested" in card["priority_factors"]


class TestHarImport:
    def _har(self, cookie_value="sekrit-session-cookie"):
        return json.dumps(
            {
                "log": {
                    "entries": [
                        {
                            "request": {
                                "method": "GET",
                                "url": "https://api.example.com/orders/1",
                                "headers": [
                                    {"name": "Cookie", "value": f"session={cookie_value}"},
                                    {"name": "Accept", "value": "application/json"},
                                ],
                            },
                            "response": {
                                "status": 200,
                                "headers": [{"name": "Content-Type", "value": "application/json"}],
                                "content": {"text": '{"id": 1}'},
                            },
                        },
                        {
                            "request": {
                                "method": "GET",
                                "url": "https://api.example.com/orders/2",
                                "headers": [],
                            },
                            "response": {
                                "status": 403,
                                "headers": [],
                                "content": {"text": "forbidden"},
                            },
                        },
                    ]
                }
            }
        )

    def test_import_flow_and_redaction(self, client, settings):
        me = register_user(client)
        csrf = me["csrf_token"]
        pid = _program(client, csrf)["id"]

        r = client.post(
            f"/api/v1/traffic/import?program_id={pid}",
            files={"file": ("test.har", io.BytesIO(self._har().encode()), "application/json")},
            headers={"X-CSRF-Token": csrf},
        )
        assert r.status_code == 202, r.text

        imports = client.get(f"/api/v1/traffic/imports?program_id={pid}").json()
        assert imports[0]["status"] == "completed"
        assert imports[0]["counts"]["imported"] == 2

        txs = client.get(f"/api/v1/traffic/transactions?program_id={pid}").json()
        assert txs["total"] == 2

        # Redaction: cookie value must never be stored.
        detail = client.get(f"/api/v1/traffic/transactions/{txs['items'][0]['id']}").json()
        assert "sekrit-session-cookie" not in json.dumps(detail)

    def test_malformed_har_rejected(self, client):
        me = register_user(client)
        csrf = me["csrf_token"]
        pid = _program(client, csrf)["id"]
        r = client.post(
            f"/api/v1/traffic/import?program_id={pid}",
            files={"file": ("bad.har", io.BytesIO(b"not json"), "application/json")},
            headers={"X-CSRF-Token": csrf},
        )
        assert r.status_code == 202
        import_job_id = r.json()["import_job_id"]
        imports = client.get("/api/v1/traffic/imports").json()
        job = next(i for i in imports if i["id"] == import_job_id)
        assert job["status"] == "failed"
        assert job["error_code"] == "PARSE_ERROR"

    def test_wrong_extension_rejected(self, client):
        me = register_user(client)
        csrf = me["csrf_token"]
        pid = _program(client, csrf)["id"]
        r = client.post(
            f"/api/v1/traffic/import?program_id={pid}",
            files={"file": ("evil.exe", b"x", "application/octet-stream")},
            headers={"X-CSRF-Token": csrf},
        )
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "UPLOAD_REJECTED"


class TestComparison:
    def test_review_required_on_status_only_diff(self, client):
        me = register_user(client)
        csrf = me["csrf_token"]
        pid = _program(client, csrf)["id"]

        tx_ids = []
        for account, status in (("acct-a", 200), ("acct-b", 200)):
            r = client.post(
                "/api/v1/traffic/transactions",
                json={
                    "program_id": pid,
                    "account_tag": account,
                    "method": "GET",
                    "url": "https://api.example.com/orders/1",
                    "response_status": status,
                    "response_headers": {"Content-Type": "application/json"},
                    "response_body": '{"id": 1}',
                },
                headers=csrf_headers(csrf),
            )
            assert r.status_code == 200
            tx_ids.append(r.json()["id"])

        # Make B return 403 with identical body (status-code-only difference).
        r = client.post(
            "/api/v1/traffic/transactions",
            json={
                "program_id": pid,
                "account_tag": "acct-c",
                "method": "GET",
                "url": "https://api.example.com/orders/1",
                "response_status": 403,
                "response_headers": {"Content-Type": "application/json"},
                "response_body": '{"id": 1}',
            },
            headers=csrf_headers(csrf),
        )
        tx_ids.append(r.json()["id"])

        r = client.post(
            "/api/v1/comparisons",
            json={"program_id": pid, "name": "status check", "transaction_ids": [tx_ids[0], tx_ids[2]]},
            headers=csrf_headers(csrf),
        )
        assert r.status_code == 200, r.text
        set_id = r.json()["id"]

        cmp = client.get(f"/api/v1/comparisons/{set_id}").json()
        assert cmp["status_diff"] is True
        assert cmp["review_required"] is True
        assert "does not indicate a vulnerability" in cmp["review_reason"]

    def test_dynamic_value_normalization(self, client):
        me = register_user(client)
        csrf = me["csrf_token"]
        pid = _program(client, csrf)["id"]
        txs = []
        for account, body in [
            ("a", '{"id": 1, "created": "2026-10-29T10:00:00Z", "uuid": "123e4567-e89b-12d3-a456-426614174000"}'),
            ("b", '{"id": 1, "created": "2026-10-30T11:11:11Z", "uuid": "999e4567-e89b-12d3-a456-426614174999"}'),
        ]:
            r = client.post(
                "/api/v1/traffic/transactions",
                json={
                    "program_id": pid,
                    "account_tag": account,
                    "method": "GET",
                    "url": "https://api.example.com/orders/1",
                    "response_status": 200,
                    "response_headers": {},
                    "response_body": body,
                },
                headers=csrf_headers(csrf),
            )
            txs.append(r.json()["id"])
        r = client.post(
            "/api/v1/comparisons",
            json={"program_id": pid, "name": "norm", "transaction_ids": txs},
            headers=csrf_headers(csrf),
        )
        cmp = client.get(f"/api/v1/comparisons/{r.json()['id']}").json()
        assert cmp["body_diff"] == []  # timestamps/uuid masked -> identical
        assert cmp["review_required"] is False


class TestFindingsHonesty:
    def test_verified_requires_human_confirmation(self, client):
        me = register_user(client)
        csrf = me["csrf_token"]
        pid = _program(client, csrf)["id"]
        r = client.post(
            "/api/v1/findings",
            json={"program_id": pid, "title": "IDOR in orders", "category": "object_access"},
            headers=csrf_headers(csrf),
        )
        fid = r.json()["id"]

        r = client.post(
            f"/api/v1/findings/{fid}/transition",
            json={"to": "under_investigation"},
            headers=csrf_headers(csrf),
        )
        assert r.status_code == 200

        # API refuses verification without explicit human confirmation.
        r = client.post(
            f"/api/v1/findings/{fid}/transition",
            json={"to": "verified", "verified_human_confirmation": False},
            headers=csrf_headers(csrf),
        )
        assert r.status_code == 403
        assert r.json()["error"]["code"] == "FORBIDDEN"

        # With confirmation it succeeds and sets validation.
        r = client.post(
            f"/api/v1/findings/{fid}/transition",
            json={"to": "verified", "verified_human_confirmation": True},
            headers=csrf_headers(csrf),
        )
        assert r.status_code == 200
        assert r.json()["status"] == "verified"
        assert r.json()["validation_status"] == "verified_human"

    def test_scanner_observation_stays_unverified(self, db, client):
        """Ingested scanner findings are `potential`/`unverified` by construction."""
        from app.db.models import Finding
        from app.domain.scope import Policy
        from app.integrations.tools.base import Observation
        from app.services.ingestion import ingest

        me = register_user(client)
        csrf = me["csrf_token"]
        pid = _program(client, csrf)["id"]
        _rule(client, csrf, pid)

        from app.db.models import Program

        program = db.get(Program, pid)
        policy = Policy.from_db_rules(program.scope_rules)
        obs = Observation(
            kind="scanner_finding",
            payload={
                "template_id": "http/misconfiguration/cors/cors-allow-all.yaml",
                "name": "CORS Allow All",
                "severity": "low",
                "matched_at": "https://api.example.com/x",
            },
            source="nuclei",
        )
        ingest(db, program, obs, policy, tool_run_id=None)
        db.commit()

        finding = db.query(Finding).filter(Finding.discovery_source == "tool_observation").first()
        assert finding is not None
        assert finding.status == "potential"
        assert finding.validation_status == "unverified"

    def test_duplicate_detection_and_linking(self, client):
        me = register_user(client)
        csrf = me["csrf_token"]
        pid = _program(client, csrf)["id"]
        r1 = client.post(
            "/api/v1/findings",
            json={"program_id": pid, "title": "IDOR on orders endpoint", "category": "object_access"},
            headers=csrf_headers(csrf),
        ).json()
        r2 = client.post(
            "/api/v1/findings",
            json={"program_id": pid, "title": "IDOR on orders endpoint (duplicate)", "category": "object_access"},
            headers=csrf_headers(csrf),
        ).json()

        dups = client.get(f"/api/v1/findings/{r1['id']}/duplicates").json()
        assert len(dups) >= 1
        assert dups[0]["finding_id"] == r2["id"]

        r = client.post(
            f"/api/v1/findings/{r1['id']}/links",
            json={"linked_finding_id": r2["id"], "kind": "duplicate_of", "note": "same bug"},
            headers=csrf_headers(csrf),
        )
        assert r.status_code == 200
        assert client.get(f"/api/v1/findings/{r1['id']}").json()["status"] == "duplicate"


class TestEvidence:
    def test_upload_download_integrity_and_delete(self, client):
        me = register_user(client)
        csrf = me["csrf_token"]
        pid = _program(client, csrf)["id"]
        content = b"evidence content" * 100

        r = client.post(
            f"/api/v1/evidence?program_id={pid}",
            files={"file": ("notes.txt", io.BytesIO(content), "text/plain")},
            headers={"X-CSRF-Token": csrf},
        )
        assert r.status_code == 201, r.text
        ev = r.json()
        assert ev["sha256"] == hashlib.sha256(content).hexdigest()

        dl = client.get(f"/api/v1/evidence/{ev['id']}/download")
        assert dl.status_code == 200
        assert dl.content == content

        r = client.delete(f"/api/v1/evidence/{ev['id']}", headers=csrf_headers(csrf))
        assert r.status_code == 200
        assert client.get(f"/api/v1/evidence/{ev['id']}/download").status_code == 404

    def test_disallowed_extension_rejected(self, client):
        me = register_user(client)
        csrf = me["csrf_token"]
        pid = _program(client, csrf)["id"]
        r = client.post(
            f"/api/v1/evidence?program_id={pid}",
            files={"file": ("payload.exe", io.BytesIO(b"MZ...."), "application/octet-stream")},
            headers={"X-CSRF-Token": csrf},
        )
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "UPLOAD_REJECTED"

    def test_oversize_rejected(self, client, settings):
        me = register_user(client)
        csrf = me["csrf_token"]
        pid = _program(client, csrf)["id"]
        big = b"a" * (settings.evidence_max_mb * 1024 * 1024 + 10)
        r = client.post(
            f"/api/v1/evidence?program_id={pid}",
            files={"file": ("big.txt", io.BytesIO(big), "text/plain")},
            headers={"X-CSRF-Token": csrf},
        )
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "UPLOAD_REJECTED"


class TestReports:
    def test_report_generation_all_formats(self, client):
        me = register_user(client)
        csrf = me["csrf_token"]
        pid = _program(client, csrf)["id"]
        fid = client.post(
            "/api/v1/findings",
            json={
                "program_id": pid,
                "title": "IDOR in orders",
                "description": "Object-level access issue",
                "severity": "high",
                "impact": "Account data disclosure",
                "reproduction_steps": "1. Login as A. 2. Fetch order of B.",
            },
            headers=csrf_headers(csrf),
        ).json()["id"]

        for fmt in ("markdown", "json", "html"):
            r = client.post(
                "/api/v1/reports",
                json={"finding_id": fid, "format": fmt},
                headers=csrf_headers(csrf),
            )
            assert r.status_code == 201, r.text
            content = r.json()["content"]
            # Honesty: unverified banner present in every format.
            if fmt == "json":
                assert '"verification_status": "unverified"' in content
            else:
                assert "UNVERIFIED" in content

        reports = client.get("/api/v1/reports").json()
        assert len(reports) == 3


class TestOverview:
    def test_overview_counts(self, client):
        me = register_user(client)
        csrf = me["csrf_token"]
        _program(client, csrf)
        r = client.get("/api/v1/overview")
        assert r.status_code == 200
        body = r.json()
        assert body["program_count"] == 1
        assert body["asset_count"] == 0
        assert body["research_queue"] == []
        assert body["recent_activity"]  # program.created audit events
