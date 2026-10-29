"""HunterFlow demo target - a SYNTHETIC, intentionally inconsistent application.

Purpose: local, harmless test fixtures for HunterFlow integration tests, E2E
tests, and demos. This application is deliberately vulnerable in documented,
harmless ways (e.g., object-level access without ownership checks). It exists
only for controlled local testing — it is NOT a real product and its flaws are
NOT real vulnerability findings.

Known expected results (documented for tests):
- GET /api/orders/{id}   : readable by ANY authenticated role (by design, BOLA fixture)
- GET /api/orders        : lists ALL orders regardless of owner (by design)
- GET /api/admin/stats   : 403 unless role=admin
- GET /api/v1/version    : public
- POST /api/login        : alice / bob / carol (carol is admin)

Run: uvicorn demo.app:app --host 0.0.0.0 --port 8080
"""

from __future__ import annotations

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI(title="HunterFlow Demo Target (synthetic, intentionally flawed)", version="0.1.0")

USERS = {
    "alice": {"password": "alice-password-123", "role": "user", "user_id": 1},
    "bob": {"password": "bob-password-123", "role": "user", "user_id": 2},
    "carol": {"password": "carol-password-123", "role": "admin", "user_id": 3},
}

ORDERS = [
    {"id": 1, "user_id": 1, "item": "laptop", "price": 999, "status": "shipped"},
    {"id": 2, "user_id": 1, "item": "keyboard", "price": 89, "status": "delivered"},
    {"id": 3, "user_id": 2, "item": "monitor", "price": 299, "status": "pending"},
    {"id": 4, "user_id": 2, "item": "dock", "price": 149, "status": "shipped"},
    {"id": 5, "user_id": 3, "item": "server", "price": 1999, "status": "delivered"},
]

SESSIONS: dict[str, str] = {}  # token -> username


class LoginBody(BaseModel):
    username: str
    password: str


def current_user(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.removeprefix("Bearer ")
    username = SESSIONS.get(token)
    if username is None:
        raise HTTPException(status_code=401, detail="invalid token")
    return USERS[username]


@app.get("/", response_class=HTMLResponse)
def index():
    # Simple HTML so a crawler has something to follow in the local demo.
    return """<!doctype html>
<html><head><title>HunterFlow demo target</title></head>
<body>
  <h1>HunterFlow demo target</h1>
  <p>Synthetic, intentionally inconsistent app for local testing only.</p>
  <ul>
    <li><a href="/api/v1/version">version</a></li>
    <li><a href="/api/v1/status">status</a></li>
    <li><a href="/api/users/me">me</a></li>
    <li><a href="/api/orders">orders</a></li>
    <li><a href="/api/orders/1">order 1</a></li>
    <li><a href="/api/orders/2">order 2</a></li>
    <li><a href="/api/admin/stats">admin stats</a></li>
    <li><a href="/docs">docs</a></li>
  </ul>
</body></html>"""


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/api/v1/version")
def version():
    return {"version": "1.2.3", "environment": "demo"}


@app.get("/api/v1/status")
def status():
    # Added to exercise monitoring/auto-card behaviour in the demo.
    return {"status": "operational", "version": "1.2.3"}


@app.post("/api/login")
def login(body: LoginBody):
    user = USERS.get(body.username)
    if user is None or user["password"] != body.password:
        raise HTTPException(status_code=401, detail="invalid credentials")
    token = f"demo-token-{body.username}-{len(SESSIONS)}"
    SESSIONS[token] = body.username
    return {"token": token, "role": user["role"]}


@app.get("/api/users/me")
def me(user: dict = Depends(current_user)):
    return {"user_id": user["user_id"], "username": user.get("user_id"), "role": user["role"]}


@app.get("/api/orders")
def list_orders(user: dict = Depends(current_user)):
    # BY DESIGN: returns all orders without ownership filtering (BOLA fixture).
    return {"orders": ORDERS}


@app.get("/api/orders/{order_id}")
def get_order(order_id: int, user: dict = Depends(current_user)):
    # BY DESIGN: no ownership check (BOLA fixture).
    for order in ORDERS:
        if order["id"] == order_id:
            return {"order": order}
    raise HTTPException(status_code=404, detail="order not found")


@app.get("/api/admin/stats")
def admin_stats(user: dict = Depends(current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="admin role required")
    return {"total_orders": len(ORDERS), "total_users": len(USERS)}
