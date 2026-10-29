# ADR-005 — PostgreSQL Primary, SQLite Dev-Only

- **Status:** Proposed (G2)
- **Date:** 2026-10-29

## Decision

PostgreSQL is the only supported runtime database. SQLite is allowed for fast local unit-test iteration, never for deployment.

## Rationale

JSONB (tech, headers, progress), `timestamptz`, text search, and integrity constraints are core to the data model; parity between dev and prod avoids surprise bugs. Docker Compose already provides Postgres with zero user effort.

## Consequences

- Compose is required for a real install; acceptable per owner decision Q3.
- Tests that depend on Postgres-specific behavior run in CI with the real engine (testcontainers).
