"""Shared test fixtures: in-memory SQLite app for unit/integration tests.

PostgreSQL is the supported runtime (ADR-005); tests here run against SQLite
for speed, and the CI job runs the same suite against a real PostgreSQL
service container via HF_DATABASE_URL.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db.base import Base, build_engine, build_session_factory
from app.main import create_app


def make_settings(tmp_path) -> Settings:
    return Settings(
        env="test",
        secret_key="test-secret-key",
        database_url=f"sqlite+pysqlite:///{tmp_path}/test.db",
        data_dir=tmp_path / "data",
    )


@pytest.fixture()
def settings(tmp_path) -> Settings:
    return make_settings(tmp_path)


@pytest.fixture()
def app(settings):
    app = create_app(settings)
    engine = build_engine(settings)
    Base.metadata.create_all(engine)
    app.state.engine = engine
    app.state.session_factory = build_session_factory(engine)
    return app


@pytest.fixture()
def client(app):
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture()
def db(app):
    factory = app.state.session_factory
    session = factory()
    try:
        yield session
    finally:
        session.close()
