"""Health endpoints (liveness/readiness) - no auth required."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text

from ..deps import get_db

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@router.get("/readyz")
def readyz(db=Depends(get_db)) -> dict:
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=503, content={"status": "not_ready"})
