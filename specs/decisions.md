# HunterFlow — Decision Log & Approval Records

- **Convention:** This file is the single source of truth for human approvals and material project decisions. Entries are chronological and immutable; corrections are new entries, not edits.

---

## Approval Records

| # | Gate | Document(s) | Version | Status | Approved by | Date (UTC) | Evidence |
|---|---|---|---|---|---|---|---|
| 1 | G1 | Constitution | 0.1.0 | **APPROVED** | Project owner | 2026-10-29 | Owner message: "all aproved continue" |
| 2 | G2 | product-requirements.md + architecture/* + adr/* | 0.1.0 | **APPROVED** | Project owner | 2026-10-29 | Owner message: "G2 — Product Requirements & Architecture: APPROVED" |
| 3 | G3 | design/* | 0.1.0 | **APPROVED** | Project owner | 2026-10-29 | Owner message: "G3 — UI/UX & Design System: APPROVED" |
| 4 | G4 | tasks/milestones/testing-strategy/release-plan | 0.1.0 | **APPROVED** | Project owner | 2026-10-29 | Owner message: "G4 — Implementation Plan: APPROVED" |

**Approved baseline:** SHA-256 hashes of all approved specification documents are recorded in `specs/approved-baseline.sha256` (36 files, computed 2026-10-29). Implementation was authorized for the full v0.1.0 roadmap (M1–M6) in the same message.

**Owner-confirmed requirement decisions (2026-10-29):**
- HF-FR-011 (auto scope extraction): Won't — manual scope configuration only. Confirmed.
- HF-FR-110 (deterministic prioritization): Must. Confirmed.
- HF-FR-180 (light theme): Could. Confirmed; dark theme prioritized.
- Architecture + all 10 ADRs: confirmed as approved.

## Open Question Resolutions (approved 2026-10-29, owner: "all aproved")

| # | Question | Decision | Rationale |
|---|---|---|---|
| Q1 | Repository location | `C:\Users\fozma\Projects\hunterflow` | Confirmed by owner. |
| Q2 | License | **MIT** | Matches ProjectDiscovery ecosystem (bundled tools MIT/Apache/BSD); maximizes adoption. See ADR-006. |
| Q3 | Database | PostgreSQL primary via Docker Compose; SQLite dev-only convenience, not a supported runtime target | Data integrity + jsonb + production-parity; Docker already required for toolchain. See ADR-005. |
| Q4 | Worker queue | **Dramatiq + Redis** (recommendation resolved) | Right-sized vs Celery; simpler than full-async ARQ; sync SQLAlchemy avoids async complexity for contributors. See ADR-003. |
| Q5 | Tool execution | Tools bundled in the worker container image | Reproducible, pinned versions; no host dependency; avoids Docker-out-of-Docker. See ADR-004. |
| Q6 | Demo target | In-repo synthetic vulnerable app (`demo/`), local-only, clearly labeled, known expected results | Required for integration/E2E tests without third-party targets. See testing-strategy. |
| Q7 | Nuclei usage | User-curated safe template subset; explicit per-scan selection; no auto-full-template runs | Constitutional P2/P4 compliance. |

## Material Design Decisions (awaiting G2 ratification)

| # | Decision | ADR |
|---|---|---|
| D1 | Modular monolith, API + separate worker process | ADR-002 |
| D2 | Sync SQLAlchemy 2 + psycopg3; FastAPI sync endpoints for DB-heavy paths | ADR-001 |
| D3 | Server-side opaque sessions in DB (no JWT) | ADR-007 |
| D4 | Evidence files on disk + DB metadata | ADR-008 |
| D5 | Deterministic rule-based prioritization first | ADR-009 |
| D6 | Cooperative job cancellation (dramatiq-abort + subprocess kill) | ADR-010 |

## Post-Approval Change Records

| # | Date | Change | Authorization | Impact |
|---|---|---|---|---|
| C1 | 2026-10-29 | v0.2 monitoring delivered (schedules, change detection, webhooks, scheduler service) | Owner instruction to add continuous monitoring for server use | Additive; no change to scope enforcement or security model |
| C2 | 2026-10-29 | v0.2.1 tool expansion: added `dnsx` and `gau` adapters and a `url_discovery` profile | Owner instruction "sıradaki adımları yap" (do the next steps) | Additive adapters behind the same scope-policy gate; DNS and historical URLs stored as assets, not probed automatically |

| C3 | 2026-10-29 | v0.3: PDF reports, optional AI assistant (OpenAI-compatible, disabled by default), team workspace with admin user management | Owner instruction to add AI via API and the remaining roadmap items | Additive; AI has no tool access and is advisory only; users share one workspace (no per-user isolation) |


| C4 | 2026-10-29 | v0.4: richer change detection (status/tech, new JS files) and optional screenshot support (separate build arg, chromium image) | Owner instruction | Additive; screenshots are opt-in, stored on the data volume, served only through an authenticated endpoint |


| C5 | 2026-10-29 | v0.5: optional auto draft research cards from monitoring changes; web_crawl profile; katana container resolver | Owner instruction | Additive, opt-in per schedule; auto-created cards require human review and are deduplicated per endpoint |


| C6 | 2026-10-29 | v0.6: dependency security upgrades (FastAPI/Starlette/uvicorn, Next/React/zod), security headers, benchmarks, production checklist | Owner instruction to run security/performance tests and prepare go-live | No scope change; login rate limit made configurable for automated tests; Next 16 async params migration |

