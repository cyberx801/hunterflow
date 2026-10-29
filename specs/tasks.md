# HunterFlow — Implementation Tasks

- **Version:** 0.1.0 (Draft for G4)
- Convention: tasks are small, independently verifiable, dependency-ordered. AC = acceptance criteria; V = verification. Only implement after G4 approval; incomplete prerequisites block a task. Requirement traceability in `[]`.

---

## Milestone 1 — Foundation

| ID | Task | Deps | Affects | AC | V |
|---|---|---|---|---|---|
| T-001 | Repo scaffold: monorepo layout, .gitignore, .env.example, Makefile, LICENSE (MIT), CONTRIBUTING/CODE_OF_CONDUCT/SECURITY/CHANGELOG stubs, issue/PR templates | — | repo root | Docs present; git clean rules work | review + `git check-ignore` smoke |
| T-002 | Backend skeleton: FastAPI app factory, config (pydantic-settings), structlog, error envelope, correlation middleware, health endpoints, router registry | — | `backend/app/{main,core}` | App boots; `/healthz` 200; error envelope unit-tested | pytest |
| T-003 | DB setup: SQLAlchemy base, session mgmt, Alembic init, user/session tables migration | T-002 | `backend/app/db`, `alembic/` | `alembic upgrade head` on empty DB; testcontainers test | pytest integration |
| T-004 | Auth: Argon2id hashing, session store, login/logout/me, CSRF token issue/verify, rate limiting, first-run account creation | T-003 | `backend/app/core/security.py`, `api/v1/auth.py` | HF-FR-120/121, HF-SEC-001/003/011 tests pass | pytest + security suite |
| T-005 | Audit log service + API | T-003 | `backend/app/core/audit.py`, `api/v1/audit.py` | Append-only endpoint; events recorded | pytest |
| T-006 | Frontend skeleton: Next app, design tokens (design-system.md), shell layout (sidebar/topbar), 10 nav routes with empty states, login + first-run pages | — | `web/app`, `web/components/layout` | All routes render; tokens match spec | Playwright smoke |
| T-007 | API client + TanStack Query setup + auth flows wired | T-004, T-006 | `web/lib`, `web/features/auth` | Login/logout E2E; session survives reload | Playwright |
| T-008 | Docker Compose: db, redis, api, worker (Dramatiq boot), web; volumes; healthchecks; alembic on boot | T-003, T-006 | `docker-compose.yml`, Dockerfiles | Clean clone → up → app usable (M1 DoD) | manual + CI compose validate |
| T-009 | CI: lint/type/unit (backend), lint/type (frontend), gitleaks, pip-audit, npm audit | T-002, T-006 | `.github/workflows/` | All green on main | CI run |

## Milestone 2 — Program & Recon

| ID | Task | Deps | Affects | AC | V |
|---|---|---|---|---|---|
| T-020 | Programs CRUD + list/search/filter API + audit | T-004 | `api/v1/programs.py`, `services/program_service.py` | HF-FR-001…004 | pytest |
| T-021 | Scope engine: rules, Policy.evaluate, exclusions, CIDR, restrictors, confirmation derivation (pure) | — | `domain/scope/` | HF-FR-005/007 semantics; exhaustive tests incl. property tests | pytest (≥95% cov) |
| T-022 | Scope rules CRUD API + policy versioning + diff + snapshot | T-020, T-021 | `api/v1/scopes.py`, `services/` | HF-FR-008; version on change; snapshot JSONB | pytest |
| T-023 | Target confirmation API (explicit allow) + audit | T-022 | `api/v1/scopes.py` | HF-FR-009 gating works end-to-end | pytest + security |
| T-024 | Adapter protocol + registry + tool detection service | — | `integrations/tools/{base,registry}.py` | HF-FR-020/021 | pytest |
| T-025 | Adapters: subfinder, httpx, katana (arg builders + parsers + golden fixtures) | T-024 | `integrations/tools/`, `parsers/` | HF-FR-026/030; redaction on args; injection tests | pytest + security |
| T-026 | Scan profiles (declarative pipelines) | T-024 | `domain/` or `jobs/profiles.py` | HF-FR-022 serializable | pytest |
| T-027 | Scan job: model, create API (policy pre-flight), enqueue, status/progress endpoints | T-022, T-026 | `api/v1/scans.py`, `jobs/` | HF-FR-023/024 API surface | pytest integration |
| T-028 | Pipeline runner: step execution, policy filter per target, normalization persistence, progress, retries, failure classification | T-025, T-027 | `jobs/pipeline.py`, `services/` | HF-FR-024/027/029/030 | pytest + fake adapter |
| T-029 | Cancellation: flag + dramatiq-abort + subprocess group kill | T-028 | `jobs/`, `integrations/tools/base.py` | HF-FR-024; <5s kill; status persisted | pytest + timing assert |
| T-030 | Dry-run mode | T-027 | `jobs/`, API | HF-FR-028; zero network (asserted) | pytest |
| T-031 | Tool runs history API + job detail UI | T-028, T-007 | `api/v1/jobs.py`, `web/features/recon` | HF-FR-025; args redacted | pytest + Playwright |
| T-032 | Nuclei adapter + curated template subset + templates.lock | T-025 | `integrations/`, `integrations/nuclei-templates-curated/` | HF-SEC/Constitution P4: explicit selection only; lockfile w/ sha256+license | pytest + review |
| T-033 | Program + scope UI (forms, rule table, preview panel, version diff, confirmation dialog) | T-022, T-023, T-020 | `web/features/programs`, `web/components/domain` | HF-FR-005/006/008/009; F2 flow | Playwright |

## Milestone 3 — Asset Intelligence

| ID | Task | Deps | Affects | AC | V |
|---|---|---|---|---|---|
| T-040 | Asset model + normalization + dedup keys (pure) | T-021 | `domain/assets/` | HF-FR-041 equivalence classes | pytest (≥95%) |
| T-041 | Observation models + persistence + provenance links | T-028, T-040 | `services/`, models | HF-FR-042; raw immutable | pytest |
| T-042 | Ingestion service (pipeline → assets/endpoints, idempotent) | T-041 | `services/ingestion.py` | Re-import no dups; provenance appended | pytest |
| T-043 | Assets API: list/detail, filters/sort/search, tags | T-040 | `api/v1/assets.py` | HF-FR-043/044; HF-PER-001 budget | pytest + bench |
| T-044 | Endpoint model + categorization + auth indicators (pure parts) | T-040 | `domain/endpoints/` | HF-FR-050/051 | pytest |
| T-045 | Endpoints API: list/detail, category override | T-044 | `api/v1/endpoints.py` | HF-FR-052 | pytest |
| T-046 | Assets + Endpoints UI (tables, filters, details, actions) | T-043, T-045, T-033 | `web/features/{assets,endpoints}` | S6/S7 specs; saved filters | Playwright |
| T-047 | Scope-status recompute on policy change (cache invalidation) | T-042, T-022 | `services/` | Status updates after policy version bump | pytest |

## Milestone 4 — Research Workspace

| ID | Task | Deps | Affects | AC | V |
|---|---|---|---|---|---|
| T-060 | Research card model + state machine (pure) | T-040 | `domain/state/`, models | HF-FR-060/061; illegal transitions rejected | pytest |
| T-061 | Cards API (CRUD, filters, history, saved filters) | T-060, T-045 | `api/v1/research.py` | HF-FR-060…064 | pytest |
| T-062 | Templates + checklists | T-061 | models + API | HF-FR-062 instantiation | pytest |
| T-063 | Research UI: board/list, card detail, template picker, history timeline | T-061, T-062 | `web/features/research` | S8 spec; F4 flow | Playwright |
| T-064 | Redaction engine (core) | T-004 | `core/redaction.py` | HF-SEC-007 patterns | pytest + security |
| T-065 | HAR parser (streaming, caps, base64) | T-064 | `integrations/parsers/har.py` | HF-FR-070 malformed/oversize handling | pytest |
| T-066 | HAR import job + transactions storage + account tags | T-065, T-042 | `jobs/`, models, `api/v1/traffic.py` | HF-FR-070/076; tokens never stored | pytest + security |
| T-067 | Traffic list/detail API + UI (viewers, truncation) | T-066 | API + `web/features/traffic` | HF-FR-072; S9 | pytest + Playwright |
| T-068 | Normalization profiles + diff engine (pure) | T-066 | `domain/compare/` | HF-FR-074 golden files | pytest |
| T-069 | Comparison API + UI (panes, synced scroll, review notice, sets, links) | T-068, T-067, T-061 | API + `web/features/traffic/compare` | HF-FR-073/075; F5 flow; no auto-finding | pytest + Playwright |

## Milestone 5 — Findings, Evidence, Reports

| ID | Task | Deps | Affects | AC | V |
|---|---|---|---|---|---|
| T-080 | Finding model + status/validation state machines (pure) | T-060 | `domain/state/`, models | HF-FR-080/081/082; scanner import stays unverified | pytest + security |
| T-081 | Findings API (CRUD, filters, transition endpoints, audit) | T-080, T-045 | `api/v1/findings.py` | HF-FR-080/081; HF-SEC honesty | pytest + security |
| T-082 | Duplicate detection (pure) + candidate linking API/UI | T-081 | `domain/dedup/`, API | HF-FR-083; provenance preserved | pytest |
| T-083 | Evidence store: upload validation, hash, download, delete, retention | T-066 | `services/evidence.py`, `api/v1/evidence.py` | HF-FR-090/091; HF-SEC-008/009 | pytest + security |
| T-084 | Evidence links (findings/cards/transactions) + UI picker | T-083, T-061 | API + `web/features/findings` | HF-FR-064/083 | pytest + Playwright |
| T-085 | Prioritization scoring (pure) + weights + API | T-040, T-044 | `domain/scoring/`, API | HF-FR-110/111/112; factor payload | pytest |
| T-086 | Findings UI (workspace, evidence, duplicates, verification control) | T-081…T-085 | `web/features/findings` | S10; F6 flow; keyboard path | Playwright |
| T-087 | Report engine: Markdown/JSON/HTML templates, verification banner, golden outputs | T-081, T-083 | `services/report.py`, `api/v1/reports.py` | HF-FR-100/101; no submission path | pytest |
| T-088 | Reports UI (editor, preview, export) | T-087 | `web/features/reports` | S11; F7 flow | Playwright |
| T-089 | Overview API + UI (real data aggregates, recent changes, activity) | many | `api/v1/overview.py`, `web/features/overview` | HF-FR-170; S2; empty states | pytest + Playwright |
| T-090 | Settings API + UI (tools/auth/storage/prioritization/audit) | T-024, T-004, T-085 | API + `web/features/settings` | HF-FR-130/140; S12 | pytest + Playwright |

## Milestone 6 — Release Quality

| ID | Task | Deps | Affects | AC | V |
|---|---|---|---|---|---|
| T-100 | Demo vulnerable app (synthetic, labeled, known results) | T-008 | `demo/` | Roles/endpoints per testing-strategy §6 | pytest + Playwright |
| T-101 | E2E suite F1–F7 incl. keyboard + axe spot-checks | all M1–M5 | `web/e2e/` | All green; M6 DoD | CI |
| T-102 | Security suite completion per testing-strategy §4 | M2–M5 | `backend/tests/security/` | All cases pass | CI |
| T-103 | Performance benchmarks (10k seed, budgets HF-PER) | T-043, T-089 | `docs/benchmarks.md` | Numbers recorded; fixes if over budget | script + review |
| T-104 | Hardening: non-root images, read-only fs, no-new-privileges, healthchecks | T-008 | Dockerfiles, compose | HF-SEC-014 verified | review + CI build |
| T-105 | Docs: README (all 14 sections), dev setup, user guide, API quickstart, screenshots from real app | M1–M5 | `docs/`, README | M6 DoD; setup <30 min | fresh-machine verification |
| T-106 | Release: CHANGELOG, v0.1.0 tag, issue labels, templates final | T-105 | repo | Release checklist complete | review |
