"""Skeleton smoke tests (T-002/T-004)."""

from __future__ import annotations

from tests.helpers import register_user


def test_healthz(client):
    resp = client.get("/api/v1/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_readyz(client):
    resp = client.get("/api/v1/readyz")
    assert resp.status_code == 200


def test_correlation_id_present(client):
    resp = client.get("/api/v1/healthz")
    assert resp.headers.get("X-Correlation-Id")


def test_error_envelope(client):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401
    body = resp.json()
    assert body["error"]["code"] == "UNAUTHORIZED"
    assert body["error"]["correlation_id"]


def test_bootstrap_status(client):
    resp = client.get("/api/v1/auth/bootstrap")
    assert resp.json() == {"setup_required": True}


def test_register_then_bootstrap_status(client):
    register_user(client)
    resp = client.get("/api/v1/auth/bootstrap")
    assert resp.json() == {"setup_required": False}


def test_second_registration_rejected(client):
    register_user(client)
    resp = client.post(
        "/api/v1/auth/register", json={"username": "tester2", "password": "x" * 12}
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


def test_login_me_logout(client):
    me = register_user(client)
    assert "csrf_token" in me

    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    assert resp.json()["username"] == "tester"

    logout = client.post(
        "/api/v1/auth/logout", headers={"X-CSRF-Token": me["csrf_token"]}
    )
    assert logout.status_code == 200

    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_login_wrong_password(client):
    register_user(client)
    client.post("/api/v1/auth/logout", headers={})
    resp = client.post(
        "/api/v1/auth/login", json={"username": "tester", "password": "wrong-password"}
    )
    assert resp.status_code == 401


def test_csrf_required_on_logout(client):
    register_user(client)
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"
