# HunterFlow — Implementation Progress

- **Updated:** 2026-10-29
- **Status:** v0.2 (research workspace + continuous monitoring)

## Gates & Baseline

- G1–G4: approved 2026-10-29 (see `specs/decisions.md`); baseline hashes in `specs/approved-baseline.sha256`.

## Milestones

| Milestone | Status | Definition of Done |
|---|---|---|
| M1 Foundation | complete | scaffold, auth, migrations, Docker, CI, frontend shell |
| M2 Program & Recon | complete | scope engine + API, adapters, pipeline, dry-run, cancellation |
| M3 Asset Intelligence | complete | normalization, dedup, provenance, inventory APIs/UI |
| M4 Research Workspace | complete | cards + state machine + templates, HAR import, comparison |
| M5 Findings & Evidence | complete | lifecycle + honesty, dedup, evidence, prioritization, reports |
| M6 Release Quality | complete | security tests, E2E, benchmarks, demo, docs, screenshots |
| v0.2 Monitoring | complete | schedules, scheduler process, change detection, webhook notifications |

## Verification results (2026-10-29)

| Suite | Result |
|---|---|
| Backend unit + integration + security (pytest) | 148 passed |
| Frontend typecheck (`tsc --noEmit`) | clean |
| Frontend build (`next build`) | success |
| Playwright E2E (`workflows.spec.ts`) | 6 passed |
| Lint (`ruff`) | clean |
| Screenshots (real captures) | 12 files in `docs/screenshots/` |
| Asset list benchmark (10k rows) | p95 73 ms (budget < 500 ms) |
| Docker Compose stack (db, redis, api, worker, scheduler, web, demo) | up, healthy |
| Real `web_inventory` scan of `demo.local` | completed: subfinder + httpx + katana, 8 endpoints, 32 monitoring events |
| Scheduler | created a job automatically for a due schedule |

## Known limitations

See `docs/known-issues.md`. Main ones: single-user; removal detection is heuristic;
per-request scope control inside third-party tools is limited (documented residual risk);
no log rotation by default.

## Next

No incomplete v0.1/v0.2 tasks. Post-roadmap: v0.3 optional local AI assistant, v0.4
multi-user collaboration.
