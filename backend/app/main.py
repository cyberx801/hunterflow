"""Application factory: middleware, routers, exception handlers, bootstrap."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from .api.v1 import (
    assets,
    auth,
    endpoints,
    evidence,
    findings,
    health,
    monitoring,
    platform,
    programs,
    reports,
    research,
    scans,
    scopes,
    traffic,
)
from .core.config import Settings, get_settings
from .core.errors import install_exception_handlers
from .core.logging import configure_logging, correlation_id_var, get_logger
from .db.base import build_engine, build_session_factory
from .db.models import User

log = get_logger("hunterflow.app")


def _create_bootstrap_user(settings: Settings, factory) -> None:
    if not (settings.bootstrap_username and settings.bootstrap_password):
        return
    db = factory()
    try:
        existing = db.scalar(select(User).where(User.username == settings.bootstrap_username))
        if existing is None:
            from .core.security import hash_password

            db.add(
                User(
                    username=settings.bootstrap_username,
                    password_hash=hash_password(settings.bootstrap_password),
                )
            )
            db.commit()
            log.info("bootstrap_user_created", username=settings.bootstrap_username)
    finally:
        db.close()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings)
    settings.ensure_data_dirs()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine = build_engine(settings)
        factory = build_session_factory(engine)
        app.state.engine = engine
        app.state.session_factory = factory
        _create_bootstrap_user(settings, factory)
        yield
        engine.dispose()

    app = FastAPI(
        title="HunterFlow API",
        version="0.2.0",
        docs_url=None if settings.is_production else "/docs",
        openapi_url=None if settings.is_production else "/openapi.json",
        lifespan=lifespan,
    )

    install_exception_handlers(app)

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.middleware("http")
    async def correlation_middleware(request: Request, call_next):
        cid = request.headers.get("X-Correlation-Id") or uuid.uuid4().hex[:16]
        token = correlation_id_var.set(cid)
        try:
            response = await call_next(request)
        finally:
            correlation_id_var.reset(token)
        response.headers["X-Correlation-Id"] = cid
        return response

    app.include_router(health.router, prefix="/api/v1")
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(programs.router, prefix="/api/v1")
    app.include_router(scopes.router, prefix="/api/v1")
    app.include_router(scans.router, prefix="/api/v1")
    app.include_router(assets.router, prefix="/api/v1")
    app.include_router(endpoints.router, prefix="/api/v1")
    app.include_router(research.router, prefix="/api/v1")
    app.include_router(traffic.router, prefix="/api/v1")
    app.include_router(findings.router, prefix="/api/v1")
    app.include_router(evidence.router, prefix="/api/v1")
    app.include_router(reports.router, prefix="/api/v1")
    app.include_router(platform.router, prefix="/api/v1")
    app.include_router(monitoring.router, prefix="/api/v1")
    return app


app = create_app()
