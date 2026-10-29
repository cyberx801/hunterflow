# HunterFlow — Observability Architecture

- **Version:** 0.1.0 (Draft for G2) · Implements Constitution P12, HF-NFR-005.

## 1. Logging

- **structlog** JSON to stdout for api + worker; `web` uses pino-style JSON via Next.js logging config (development console stays human-readable).
- Every log line carries: `ts`, `level`, `logger`, `correlation_id`, `service`, and event name.
- **Correlation IDs:** `X-Correlation-Id` per request (generated at web, forwarded to api); jobs get their own `job:<id>` correlation id propagated into tool-run records and worker logs.
- Sensitive data never logged raw; the central redaction filter runs at the logging boundary (HF-SEC-007).

## 2. Metrics (basic, in MVP)

- `/healthz` (liveness: process up), `/readyz` (readiness: DB + Redis reachable) on api/worker/web.
- Lightweight Prometheus-style counters (via `prometheus-fastapi-instrumentator` only if trivially integrateable; otherwise custom counters exported as text) for: requests, job counts by status, tool-run durations, failures by error class. **Post-MVP** full Prometheus/Grafana stack — not in v0.1.0 scope.

## 3. Job Observability

- `scan_jobs.progress` JSONB: steps completed/total, per-step counters, current tool.
- `tool_runs`: timing, exit codes, output refs — the authoritative execution history (HF-FR-025).
- Failure classification taxonomy: `TOOL_NOT_FOUND`, `TIMEOUT`, `NONZERO_EXIT`, `POLICY_BLOCKED`, `PARSE_ERROR`, `CANCELLED`, `INFRA` — stored as `error_code`, surfaced in UI.

## 4. Audit Events (HF-FR-140)

Append-only `audit_events` via API: auth events, policy changes, confirmations, job lifecycle, finding transitions, evidence downloads, settings changes. UI: filterable table in Settings → Audit.

## 5. Operational Practice

- Graceful shutdown: drain in-flight requests; worker finishes or marks interrupted tool runs.
- Retries: bounded exponential backoff only for transient infra errors; tool steps max 2 retries.
- Health checks wired into compose `healthcheck` for db/redis/api/worker.
