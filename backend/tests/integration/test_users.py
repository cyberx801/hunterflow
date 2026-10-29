"""Multi-user team workspace: roles, registration policy, admin management."""

from __future__ import annotations

from tests.helpers import csrf_headers, register_user


def test_first_user_is_admin(client):
    me = register_user(client)
    assert me["is_admin"] is True
    assert client.get("/api/v1/auth/me").json()["is_admin"] is True


def test_registration_closed_after_first_user(client):
    register_user(client)
    r = client.post(
        "/api/v1/auth/register", json={"username": "second", "password": "second-password-123"}
    )
    assert r.status_code == 403


def test_registration_open_when_enabled(client, settings):
    settings.allow_registration = True
    register_user(client)
    r = client.post(
        "/api/v1/auth/register", json={"username": "second", "password": "second-password-123"}
    )
    assert r.status_code == 200
    assert r.json()["is_admin"] is False


def test_admin_manages_users_and_non_admin_forbidden(client):
    me = register_user(client)
    csrf = me["csrf_token"]

    r = client.post(
        "/api/v1/users",
        json={"username": "member", "password": "member-password-123", "is_admin": False},
        headers=csrf_headers(csrf),
    )
    assert r.status_code == 201, r.text
    member = r.json()
    assert member["is_admin"] is False

    users = client.get("/api/v1/users").json()
    assert {u["username"] for u in users} == {"tester", "member"}

    # Duplicate username rejected.
    r = client.post(
        "/api/v1/users",
        json={"username": "member", "password": "member-password-123"},
        headers=csrf_headers(csrf),
    )
    assert r.status_code == 409

    # Log in as the member and confirm admin endpoints are forbidden.
    client.cookies.clear()
    login = client.post(
        "/api/v1/auth/login", json={"username": "member", "password": "member-password-123"}
    )
    assert login.status_code == 200
    assert client.get("/api/v1/users").status_code == 403


def test_cannot_demote_last_admin_or_deactivate_self(client):
    me = register_user(client)
    csrf = me["csrf_token"]
    r = client.patch(
        f"/api/v1/users/{me['id']}", json={"is_admin": False}, headers=csrf_headers(csrf)
    )
    assert r.status_code == 400
    r = client.patch(
        f"/api/v1/users/{me['id']}", json={"is_active": False}, headers=csrf_headers(csrf)
    )
    assert r.status_code == 400


def test_deactivated_user_cannot_log_in(client):
    me = register_user(client)
    csrf = me["csrf_token"]
    member = client.post(
        "/api/v1/users",
        json={"username": "member", "password": "member-password-123"},
        headers=csrf_headers(csrf),
    ).json()
    r = client.patch(
        f"/api/v1/users/{member['id']}", json={"is_active": False}, headers=csrf_headers(csrf)
    )
    assert r.status_code == 200
    client.cookies.clear()
    login = client.post(
        "/api/v1/auth/login", json={"username": "member", "password": "member-password-123"}
    )
    assert login.status_code == 401
