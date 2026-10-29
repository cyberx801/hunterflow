"""Auth helpers for tests."""

from __future__ import annotations

from app.api.deps import CSRF_HEADER


def register_user(client, username: str = "tester", password: str = "correct-horse-battery") -> dict:
    resp = client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def login(client, username: str, password: str) -> dict:
    resp = client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def csrf_headers(csrf_token: str, extra: dict | None = None) -> dict:
    headers = {CSRF_HEADER: csrf_token, "Content-Type": "application/json"}
    if extra:
        headers.update(extra)
    return headers
