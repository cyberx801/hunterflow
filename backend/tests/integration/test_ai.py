"""Optional AI assistant: disabled by default, data-only, redacted."""

from __future__ import annotations

import json

from tests.helpers import csrf_headers, register_user


def _card(client, csrf):
    program = client.post(
        "/api/v1/programs", json={"name": "AI", "platform": "other"}, headers=csrf_headers(csrf)
    ).json()
    card = client.post(
        "/api/v1/research",
        json={
            "program_id": program["id"],
            "title": "BOLA check",
            "hypothesis": "Object-level authorization may be missing.",
            "observations_md": "Authorization: Bearer supersecret-token in a copied request",
        },
        headers=csrf_headers(csrf),
    ).json()
    return card


def test_ai_disabled_by_default(client):
    me = register_user(client)
    card = _card(client, me["csrf_token"])
    r = client.post(
        "/api/v1/ai/summarize",
        json={"kind": "research_card", "id": card["id"]},
        headers=csrf_headers(me["csrf_token"]),
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "BAD_STATE"
    status = client.get("/api/v1/ai/status").json()
    assert status["enabled"] is False


def test_ai_sends_redacted_workspace_data(client, settings, monkeypatch):
    settings.ai_enabled = True
    me = register_user(client)
    card = _card(client, me["csrf_token"])

    captured = {}

    class FakeResp:
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content": "Summary\nFacts\nNext steps\nGaps"}}]}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured["url"] = url
        captured["payload"] = json
        return FakeResp()

    monkeypatch.setattr("httpx.post", fake_post)
    r = client.post(
        "/api/v1/ai/summarize",
        json={"kind": "research_card", "id": card["id"]},
        headers=csrf_headers(me["csrf_token"]),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["text"].startswith("Summary")
    assert "not a finding" in body["disclaimer"]

    sent = json.dumps(captured["payload"])
    assert "BOLA check" in sent
    assert "supersecret-token" not in sent
    assert captured["url"].endswith("/chat/completions")


def test_ai_unreachable_reports_502(client, settings, monkeypatch):
    settings.ai_enabled = True
    me = register_user(client)
    card = _card(client, me["csrf_token"])

    def boom(*args, **kwargs):
        raise ConnectionError("no route")

    monkeypatch.setattr("httpx.post", boom)
    r = client.post(
        "/api/v1/ai/summarize",
        json={"kind": "research_card", "id": card["id"]},
        headers=csrf_headers(me["csrf_token"]),
    )
    assert r.status_code == 502
