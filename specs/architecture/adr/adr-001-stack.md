# ADR-001 — Technology Stack

- **Status:** Proposed (G2)
- **Date:** 2026-10-29

## Decision

Backend: Python 3.12+ / FastAPI / Pydantic v2 / SQLAlchemy 2 (sync) / psycopg3 / Alembic. Frontend: Next.js + TypeScript + Tailwind + shadcn/ui + TanStack Query. Database: PostgreSQL 16+. Queue: Redis + Dramatiq.

## Context

Constitution §5 pins the stack; this ADR resolves the open choices: sync vs async SQLAlchemy; the queue; the ORM driver.

## Options

1. **Fully async** (SQLAlchemy async + asyncpg + ARQ): modern, but async adds sharp edges (lazy-load pitfalls, test complexity) for contributors; blocking subprocess work still needs executors.
2. **Sync SQLAlchemy + psycopg3 + Dramatiq** (chosen): simplest mental model; FastAPI threadpool handles single-user load easily; Dramatiq workers are threads/processes — a natural fit for subprocess orchestration.
3. Celery instead of Dramatiq: more features, much more operational surface than needed.

## Consequences

- Pros: low contributor friction, fewer failure modes, simple tests.
- Cons: sync endpoints are less "trendy"; if the project later needs very high concurrency, endpoints would need conversion — acceptable at this scale.
