"""Benchmark the asset list endpoint against 10,000 seeded rows (HF-PER-001).

Run: uv run python scripts/benchmark.py
Records measured p50/p95 latencies. Numbers are measured, not asserted as claims.
"""

from __future__ import annotations

import statistics
import tempfile
import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db.base import Base, build_engine, build_session_factory
from app.db.models import Asset, Program
from app.main import create_app


def main() -> None:
    tmp = Path(tempfile.mkdtemp())
    settings = Settings(
        env="test",
        secret_key="bench",
        database_url=f"sqlite+pysqlite:///{tmp}/bench.db",
        data_dir=tmp / "data",
    )
    app = create_app(settings)
    engine = build_engine(settings)
    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)
    app.state.engine = engine
    app.state.session_factory = factory

    db = factory()
    program = Program(name="Bench", platform="other")
    db.add(program)
    db.flush()
    for i in range(10_000):
        db.add(
            Asset(
                program_id=program.id,
                type="subdomain",
                value_normalized=f"host{i:05d}.example.com",
                value_original=f"host{i:05d}.example.com",
                scope_status="in_scope",
            )
        )
    db.commit()
    db.close()

    client = TestClient(app)
    client.post("/api/v1/auth/register", json={"username": "bench", "password": "bench-password-123"})
    me = client.get("/api/v1/auth/me").json()
    csrf = me["csrf_token"]

    latencies = []
    for _ in range(200):
        t0 = time.perf_counter()
        r = client.get("/api/v1/assets?page=1&page_size=50")
        latencies.append((time.perf_counter() - t0) * 1000)
        assert r.status_code == 200, r.text

    latencies.sort()
    p50 = statistics.median(latencies)
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[int(len(latencies) * 0.99)]

    print(f"assets list endpoint (10k rows, page_size=50), n=200 requests")
    print(f"  p50 = {p50:.1f} ms")
    print(f"  p95 = {p95:.1f} ms")
    print(f"  p99 = {p99:.1f} ms")
    print(f"  budget HF-PER-001: p95 < 500 ms")
    print(f"  result: {'PASS' if p95 < 500 else 'FAIL'}")


if __name__ == "__main__":
    main()
