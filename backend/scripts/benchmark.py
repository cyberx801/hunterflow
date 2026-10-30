"""Benchmarks for the primary list endpoints (HF-PER-001).

Seeds 10,000 assets, 5,000 endpoints and 1,000 research cards, then measures
p50/p95/p99 latency for each list/overview endpoint. Numbers are measured, not
asserted as claims.

Run: uv run python scripts/benchmark.py
"""

from __future__ import annotations

import statistics
import tempfile
import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db.base import Base, build_engine, build_session_factory
from app.db.models import Asset, Endpoint, Program, ResearchCard
from app.main import create_app

BUDGET_MS = 500
REQUESTS = 100


def measure(client: TestClient, path: str) -> tuple[float, float, float]:
    latencies = []
    for _ in range(REQUESTS):
        t0 = time.perf_counter()
        r = client.get(path)
        latencies.append((time.perf_counter() - t0) * 1000)
        assert r.status_code == 200, (path, r.status_code, r.text[:200])
    latencies.sort()
    return (
        statistics.median(latencies),
        latencies[int(len(latencies) * 0.95)],
        latencies[int(len(latencies) * 0.99)],
    )


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

    first_asset = Asset(
        program_id=program.id,
        type="subdomain",
        value_normalized="host00000.example.com",
        value_original="host00000.example.com",
        scope_status="in_scope",
    )
    db.add(first_asset)
    db.flush()

    for i in range(1, 10_000):
        db.add(
            Asset(
                program_id=program.id,
                type="subdomain",
                value_normalized=f"host{i:05d}.example.com",
                value_original=f"host{i:05d}.example.com",
                scope_status="in_scope",
            )
        )
    db.flush()

    for i in range(5_000):
        db.add(
            Endpoint(
                program_id=program.id,
                asset_id=first_asset.id,
                method="GET",
                path=f"/api/v1/resource/{i}",
                category="resource_mgmt",
            )
        )
    db.flush()

    for i in range(1_000):
        db.add(
            ResearchCard(
                program_id=program.id,
                title=f"Bench card {i}",
                hypothesis="Benchmark hypothesis",
                status="not_started",
            )
        )
    db.commit()
    db.close()

    client = TestClient(app)
    client.post(
        "/api/v1/auth/register",
        json={"username": "bench", "password": "bench-password-123"},
    )

    endpoints = {
        "assets (10k rows, page=50)": "/api/v1/assets?page=1&page_size=50",
        "endpoints (5k rows, page=50)": "/api/v1/endpoints?page=1&page_size=50",
        "research (1k rows, page=50)": "/api/v1/research?page=1&page_size=50",
        "overview": "/api/v1/overview",
    }

    print(f"n={REQUESTS} requests each, SQLite dev database\n")
    print(f"{'endpoint':38} {'p50':>8} {'p95':>8} {'p99':>8}  result")
    failures = 0
    for label, path in endpoints.items():
        p50, p95, p99 = measure(client, path)
        ok = p95 < BUDGET_MS
        failures += 0 if ok else 1
        print(f"{label:38} {p50:7.1f}ms {p95:7.1f}ms {p99:7.1f}ms  {'PASS' if ok else 'FAIL'}")
    print(f"\nbudget: p95 < {BUDGET_MS} ms")
    raise SystemExit(0 if failures == 0 else 1)


if __name__ == "__main__":
    main()
