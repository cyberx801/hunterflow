# HunterFlow — Implementation Decisions

- Records material implementation decisions not already covered by ADRs (which are authoritative). Chronological.

| # | Date | Decision | Rationale |
|---|---|---|---|
| 1 | 2026-10-29 | Dev toolchain: uv (backend), npm (frontend), local Python 3.12.6; Docker for integration/E2E when daemon available | Matches environment; uv.lock satisfies ADR-001 lockfile requirement |
| 2 | 2026-10-29 | Tests that require Postgres/Redis run against real containers when Docker is up; otherwise run on SQLite + Dramatiq StubBroker and are reported as such (never silently skipped/passed) | Constitution P10 honesty; ADR-005 permits SQLite dev-only |
