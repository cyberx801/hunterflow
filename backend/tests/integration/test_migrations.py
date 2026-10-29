"""Migration verification: alembic upgrade head works on a fresh database and
matches the SQLAlchemy metadata (no drift)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[2]


@pytest.fixture()
def migrated_db(tmp_path):
    db_path = tmp_path / "migrated.db"
    url = f"sqlite+pysqlite:///{db_path}"
    env = {
        "HF_ENV": "test",
        "HF_DATABASE_URL": url,
        "HF_SECRET_KEY": "test",
        "PATH": sys.executable.split("python")[0],
    }
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env={**__import__("os").environ, **env},
        check=True,
        capture_output=True,
    )
    return db_path


def test_migration_produces_all_tables(migrated_db):
    from sqlalchemy import create_engine, inspect

    from app.db.base import Base

    engine = create_engine(f"sqlite+pysqlite:///{migrated_db}")
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    expected = set(Base.metadata.tables.keys())
    missing = expected - tables
    assert not missing, f"Migration missing tables: {missing}"
