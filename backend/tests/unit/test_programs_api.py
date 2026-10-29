"""Program + scope API tests (T-020/022/023)."""

from __future__ import annotations

from tests.helpers import csrf_headers, register_user


def _mk_program(client, csrf, name="ACME Corp"):
    resp = client.post(
        "/api/v1/programs",
        json={"name": name, "platform": "other"},
        headers=csrf_headers(csrf),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _add_rule(
    client, csrf, program_id,
    kind="domain_wildcard", value="*.example.com", effect="allow", priority=10,
):
    resp = client.post(
        f"/api/v1/programs/{program_id}/scope/rules",
        json={"kind": kind, "value": value, "effect": effect, "priority": priority},
        headers=csrf_headers(csrf),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_program_crud(client):
    me = register_user(client)
    csrf = me["csrf_token"]
    program = _mk_program(client, csrf)
    assert program["name"] == "ACME Corp"
    assert program["current_policy_version"] == 0

    resp = client.get("/api/v1/programs")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1

    resp = client.patch(
        f"/api/v1/programs/{program['id']}",
        json={"description": "updated"},
        headers=csrf_headers(csrf),
    )
    assert resp.status_code == 200
    assert resp.json()["description"] == "updated"

    resp = client.delete(
        f"/api/v1/programs/{program['id']}", headers=csrf_headers(csrf)
    )
    assert resp.status_code == 200
    assert client.get("/api/v1/programs").json()["total"] == 0


def test_program_requires_auth(client):
    assert client.get("/api/v1/programs").status_code == 401
    assert client.post("/api/v1/programs", json={"name": "x"}).status_code == 401


def test_scope_rule_lifecycle_and_preview(client):
    me = register_user(client)
    csrf = me["csrf_token"]
    program = _mk_program(client, csrf)

    rule = _add_rule(client, csrf, program["id"])
    assert rule["value"] == "*.example.com"

    resp = client.post(
        f"/api/v1/programs/{program['id']}/scope/preview",
        json={"targets": ["https://api.example.com/v1", "https://evil.net/x"]},
    )
    assert resp.status_code == 200
    results = {r["target"]: r for r in resp.json()}
    assert results["https://api.example.com/v1"]["allowed"] is True
    assert results["https://evil.net/x"]["allowed"] is False
    assert results["https://evil.net/x"]["requires_confirmation"] is True


def test_scope_deny_precedence(client):
    me = register_user(client)
    csrf = me["csrf_token"]
    program = _mk_program(client, csrf)
    _add_rule(client, csrf, program["id"], value="*.example.com", effect="allow")
    _add_rule(
        client, csrf, program["id"],
        kind="domain_exact", value="staging.example.com", effect="deny", priority=1,
    )
    resp = client.post(
        f"/api/v1/programs/{program['id']}/scope/preview",
        json={"targets": ["https://staging.example.com/x"]},
    )
    result = resp.json()[0]
    assert result["allowed"] is False
    assert result["requires_confirmation"] is False


def test_scope_invalid_rule_rejected(client):
    me = register_user(client)
    csrf = me["csrf_token"]
    program = _mk_program(client, csrf)
    resp = client.post(
        f"/api/v1/programs/{program['id']}/scope/rules",
        json={"kind": "domain_wildcard", "value": "not a domain", "effect": "allow"},
        headers=csrf_headers(csrf),
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "VALIDATION"


def test_policy_versioning(client):
    me = register_user(client)
    csrf = me["csrf_token"]
    program = _mk_program(client, csrf)
    _add_rule(client, csrf, program["id"])

    resp = client.post(
        f"/api/v1/programs/{program['id']}/scope/versions",
        json={"change_summary": "initial scope"},
        headers=csrf_headers(csrf),
    )
    assert resp.status_code == 200
    assert resp.json()["version"] == 1

    resp = client.get(f"/api/v1/programs/{program['id']}/scope/versions")
    assert resp.status_code == 200
    versions = resp.json()
    assert versions[0]["version"] == 1
    assert versions[0]["rule_count"] == 1

    detail = client.get(f"/api/v1/programs/{program['id']}/scope/versions/1")
    assert detail.status_code == 200
    assert len(detail.json()["rules"]) == 1
    assert detail.json()["previous_rules"] is None


def test_publish_empty_policy_rejected(client):
    me = register_user(client)
    csrf = me["csrf_token"]
    program = _mk_program(client, csrf)
    resp = client.post(
        f"/api/v1/programs/{program['id']}/scope/versions",
        json={},
        headers=csrf_headers(csrf),
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "BAD_STATE"
