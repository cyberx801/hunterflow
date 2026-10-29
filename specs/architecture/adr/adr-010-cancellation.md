# ADR-010 — Cooperative Job Cancellation

- **Status:** Proposed (G2)
- **Date:** 2026-10-29

## Decision

Cancellation = DB flag + `dramatiq-abort` middleware signal; the running pipeline checks between steps and kills the active subprocess group. Status transitions to `cancelled` after cleanup.

## Rationale

- Tool subprocesses can't be aborted safely by killing worker threads; process-group kill of the subprocess tree is the reliable primitive.
- Bounded latency (target <5 s) without a separate orchestrator.

## Consequences

- Each adapter exposes `kill()` (process group terminate → SIGKILL escalation).
- Partial results already persisted remain visible with job status `cancelled` (no silent data loss).
