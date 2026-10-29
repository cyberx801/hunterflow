# HunterFlow — Known Issues

| # | Date | Area | Issue | Impact | Status |
|---|---|---|---|---|---|
| 1 | 2026-10-29 | Security (residual) | Per-request scope control inside third-party tools is limited | A tool could follow a redirect after our check (TOCTOU) | Documented in `specs/architecture/security.md` §9; katana/httpx run with redirects disabled, nuclei with `-dr`; full mitigation needs a proxy gateway (post-MVP) |
| 2 | 2026-10-29 | Security (residual) | SQLite dev mode lacks PostgreSQL constraint parity | Dev only; not a supported runtime | PostgreSQL is the only supported runtime (ADR-005) |
| 3 | 2026-10-29 | Product | Single-user model: registration closes after the first account | Expected for v0.2 | By design |
| 4 | 2026-10-29 | Monitoring | Removal detection is heuristic (two consecutive misses) | A host that flaps can be reported as removed | Events are informational; verify before acting |
| 5 | 2026-10-29 | Monitoring | Passive subdomain enumeration can return irrelevant hosts for reserved names | The local `demo.local` demo shows such hosts as `needs_confirmation` | They are never probed (not in scope); harmless |
| 6 | 2026-10-29 | Perf | Tag filter on assets/endpoints is applied after pagination | Inaccurate `total` when filtering by tag | Low impact; batch DB-side filtering planned with JSONB containment |
| 7 | 2026-10-29 | Ops | No log rotation configured in compose | Docker logs can grow | Configure the Docker daemon or compose `logging` options |
| 8 | 2026-10-29 | Ops | Scheduler assumes a single instance | Running two schedulers can double-enqueue | Run exactly one `scheduler` service (compose default) |
