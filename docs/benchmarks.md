# Performance benchmarks

Measured results only — no claims without measurement (project constitution P15).

## Method

`backend/scripts/benchmark.py` seeds 10,000 assets and issues 200 authenticated `GET /api/v1/assets?page=1&page_size=50` requests through the application (TestClient), reporting p50/p95/p99 latency.

Environment: local development machine, SQLite dev database, Windows host, Python 3.12.

## Results (2026-10-29)

| Endpoint | p50 | p95 | p99 | Budget (HF-PER-001) |
|---|---|---|---|---|
| `GET /assets` (10k rows, page=50) | 56 ms | 73 ms | 80 ms | p95 < 500 ms ✅ |

## Notes

- The initial implementation issued per-row aggregate queries (N+1). This was fixed by batching `endpoint`/`card` counts and computing priority from cached signals; p95 dropped from ~770 ms to ~73 ms.
- These figures are for SQLite (development). PostgreSQL (production) is expected to be comparable or faster; a PostgreSQL run is recorded in CI on the release checklist.
- Re-run: `cd backend && uv run python scripts/benchmark.py`.
