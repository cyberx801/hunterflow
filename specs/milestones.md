# HunterFlow — Milestones & Definition of Done

- **Version:** 0.1.0 (Draft for G4)
- Task breakdown: `specs/tasks.md`. Testing: `specs/testing-strategy.md`. Release: `specs/release-plan.md`.

## M1 — Foundation

Scope: repo scaffolding, backend/frontend skeletons, DB + migrations, auth, Docker dev env, CI.

**Definition of Done:**
- `docker compose up -d` from a clean clone reaches a running, password-protected app.
- Alembic migrations apply cleanly on empty DB; first-run account creation works.
- CI runs: backend lint+type+unit, frontend lint+type, security scans (gitleaks, pip-audit, npm audit) — all green on `main`.
- Skeleton pages for all 10 nav sections render (empty states), routing works.
- Session/CSRF unit + security tests pass.

## M2 — Program & Recon

Scope: programs, scope rules, policy engine, versioning, confirmation flow, tool adapters, scan profiles, job lifecycle, execution history, dry-run.

**Definition of Done:**
- Policy engine unit tests exhaustive (wildcards, CIDR, exclusions, precedence, redirects); fuzz-tested.
- All four adapters integrated with version detection; subfinder+httpx+katana produce normalized observations in integration tests (fixture outputs; no external targets).
- Job lifecycle E2E: queue → run (demo profile) → progress → complete; cancel kills subprocess <5 s; failure classified.
- Out-of-scope fixture test proves blocked targets are never requested (security test).
- Nuclei curated subset: template list + lockfile present; execution gated behind explicit selection.

## M3 — Asset Intelligence

Scope: asset/endpoint models, normalization, dedup, provenance, inventory UI, endpoint categorization + manual correction.

**Definition of Done:**
- Normalization/dedup unit tests cover case/port/slash equivalence classes.
- Ingestion from M2 pipelines idempotent (re-import creates no duplicates; provenance rows appended).
- Asset/endpoint list APIs meet HF-PER-001 budget at 10k seeded rows (benchmark recorded, not claimed).
- UI: filtering/sorting/search/saved filters; asset+endpoint detail pages with research actions.

## M4 — Research Workspace

Scope: research cards + state machine + templates/checklists, HAR import + redaction, transactions list, comparison with normalization + diff, comparison sets.

**Definition of Done:**
- Card state machine transitions unit-tested; history preserved.
- HAR import E2E: malformed rejected; valid file imports fully; tokens redacted (security test asserts no cookie values stored).
- Diff golden-file tests prove noise normalization (timestamps/UUIDs/headers).
- Comparison workflow links a set to a research card; status-code-only differences trigger review notice (no auto-finding).

## M5 — Findings & Evidence

Scope: findings + lifecycle + duplicate detection, evidence store, prioritization scoring, report generator (Markdown/JSON/HTML).

**Definition of Done:**
- Scanner observations → findings remain `potential/unverified`; only human action sets `verified_human` (security test attempts API bypass).
- Duplicate matching unit tests; linking preserves provenance.
- Evidence: upload validation tests (type/size/magic bytes), integrity hash verify on download, direct URL access denied.
- Scoring: pure function tests; factor breakdown renders; weights configurable.
- Reports: golden-file output tests for all 3 formats; verification banner present; no submission code path.

## M6 — Release Quality

Scope: E2E suite, security tests, perf checks, demo app, docs, hardening, v0.1.0 release.

**Definition of Done:**
- Playwright E2E covers F1–F7 journeys incl. keyboard-only path; axe spot-checks pass.
- Security suite complete (spec testing-strategy §4).
- Demo app: labeled synthetic vulnerable target; documented known expected results; never claims real discovery.
- README quick start verified from a clean machine (container build from scratch).
- Performance benchmarks recorded in `docs/benchmarks.md`.
- CHANGELOG + v0.1.0 tag; issue/PR templates; SECURITY.md; license + attribution (nuclei-templates) present.

A milestone is complete only when its DoD is verified in CI and recorded — not when files exist (Constitution P10).
