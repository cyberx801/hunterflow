# ADR-003 — Queue: Dramatiq + Redis

- **Status:** Proposed (G2)
- **Date:** 2026-10-29

## Decision

Dramatiq with Redis broker for background jobs; APScheduler integration reserved for post-MVP scheduled monitoring.

## Options

| | Dramatiq | Celery | ARQ | In-process |
|---|---|---|---|---|
| Maturity | high, stable | highest | mid | — |
| Complexity | low | high (config, workers, result backends) | low | lowest |
| Async fit | sync (matches ADR-001) | both | async-only | n/a |
| Retries/timeouts/cancellation | yes / time_limit / dramatiq-abort | yes | yes | no |

## Rationale

Dramatiq matches the sync stack, supports retries, time limits, middleware-based abort, and Redis brokers. Celery solves problems (multi-tenant routing, many backends) we do not have.

## Consequences

- Cancellation is cooperative (dramatiq-abort + subprocess kill) — acceptable latency (<5 s target).
- If multi-node fleets ever arrive (non-goal), revisit Celery/other.
