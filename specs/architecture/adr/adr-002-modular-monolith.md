# ADR-002 — Modular Monolith with Isolated Worker

- **Status:** Proposed (G2)
- **Date:** 2026-10-29

## Decision

One backend codebase; API process (FastAPI) and worker process (Dramatiq) deployed as separate containers. No microservices.

## Context

Constitution P7 mandates modular monolith + isolated workers. Single-user scale; the only long-running work is tool execution.

## Rationale

- Same models/services shared via code, not network contracts — no serialization drift.
- Worker isolation gives resource caps, crash containment, cancellation without affecting the API.
- Microservices would add deployment, auth-between-services, and integration-test tax with zero user benefit.

## Consequences

- One Alembic history, one set of tests, one deployment repo.
- Scaling beyond one host would require revisiting (not planned).
