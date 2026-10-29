# HunterFlow — Known Issues

| # | Date | Area | Issue | Impact | Status |
|---|---|---|---|---|---|
| 1 | 2026-10-29 | Environment | Docker registry pull for `redis:7-alpine` failed mid-pull during local verification | Local real-scan path (non-dry-run) couldn't be exercised end-to-end on the dev host | Docker Compose provides Redis in normal use; dry-run path verified locally; worker pipeline verified via StubBroker tests |
| 2 | 2026-10-29 | Environment | Tool binaries are Linux-only; local dev host is Windows | Real-tool subprocess runs not exercised locally | Adapters verified with golden fixtures + fake binaries; binaries pinned w/ SHA-256 in `tools.lock`; CI (Linux) exercises real images |
| 3 | 2026-10-29 | Security (residual) | Per-request scope control inside third-party tools is limited | A tool could internally follow a redirect after our check (TOCTOU) | Documented in `specs/architecture/security.md` §9; no-follow flags + post-hoc violation logging; full mitigation requires a proxy gateway (post-MVP) |
| 4 | 2026-10-29 | Security (residual) | SQLite dev mode lacks row-level/JSONB constraint parity with PostgreSQL | Dev-only; not a supported runtime | PostgreSQL is the only supported runtime (ADR-005) |
| 5 | 2026-10-29 | Product | Single-user model means one account; registration disabled after first account | Expected for v0.1.0 (non-goal: multi-tenancy) | By design |
| 6 | 2026-10-29 | Perf | Tag filter on assets/endpoints is applied post-pagination | Inaccurate `total` when filtering by tag | Low impact; batch DB-side filtering planned with JSONB containment on Postgres |
