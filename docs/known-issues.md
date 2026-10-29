# HunterFlow — Known Issues

| # | Date | Area | Issue | Impact | Mitigation / Status |
|---|---|---|---|---|---|
| 1 | 2026-10-29 | Environment | Docker Desktop daemon not running at session start | Postgres/Redis integration tests, tool-image builds, E2E demo profile unavailable until daemon up | Daemon start initiated; fallback: SQLite + StubBroker test modes (reported honestly) |
| 2 | 2026-10-29 | Environment | Tool binaries (subfinder/httpx/katana/nuclei) are Linux-only in the worker image | Real-tool integration tests can't run on Windows host; verified in CI/docker instead | Golden-fixture parser tests + fake adapters cover logic locally |
