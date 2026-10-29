# HunterFlow — System Architecture

- **Version:** 0.1.0 (Draft for G2)
- **Status:** Pending approval gate G2
- **Decisions:** ADR-001…ADR-010

## 1. Topology

```
┌─────────────┐      ┌──────────────┐      ┌───────────────┐
│   Browser   │ ───► │  Web (Next)  │ ───► │  API (FastAPI)│
└─────────────┘      │  :3000       │      │  :8000        │
                     └──────────────┘      └──────┬────────┘
                                                  │
                      ┌───────────────┐           │
                      │ PostgreSQL    │ ◄─────────┤
                      │ :5432 (int)   │           │
                      └───────────────┘     ┌─────┴─────┐
                      ┌───────────────┐     │ Redis     │
                      │ Worker        │     │ :6379(int)│
                      │ (Dramatiq)    │ ◄───┴───────────┘
                      │ + tool images │
                      └───────────────┘
```

- **4 runtime services:** `web`, `api`, `worker`, `db`, `redis` (+ `demo-app` behind a compose profile for tests).
- **Modular monolith:** `api` and `worker` run the same backend codebase; the worker only boots Dramatiq consumers (ADR-002).
- **No public exposure of db/redis** (internal networks only); only `web` is exposed to the host.

## 2. Component Responsibilities

| Component | Responsibility | Does NOT do |
|---|---|---|
| **web** (Next.js) | Render UI, server-side proxy of `/api/*` to API, session cookie pass-through | No business logic, no direct DB |
| **api** (FastAPI) | REST `/api/v1`, authn/authz, CRUD, scope policy evaluation, job enqueue/status, evidence serving, reports | No long-running work, no tool execution |
| **worker** (Dramatiq) | Tool execution via adapters, job lifecycle updates, normalization + persistence of observations, policy enforcement before outbound ops | No HTTP API |
| **db** | Source of truth for all normalized data | — |
| **redis** | Job queue + locks + cache of job progress | Not a data store of record |

## 3. Core Data Flows

1. **Scan job:** UI → API `POST /scans` (validates targets vs policy version) → row `scan_jobs(queued)` + enqueue Dramatiq message → worker executes pipeline: for each step, adapter builds args → policy check per target → subprocess → parse JSONL → normalize → persist observations/assets/endpoints → progress updates via Redis → final status.
2. **Scope evaluation:** pure function `Policy.evaluate(host, method, path)` → `Decision{allowed, matched_rules[], requires_confirmation}`. Used by API (pre-flight), worker (per target), and preview UI. Single source of truth (ADR on P2 in constitution §5.4).
3. **HAR import:** UI uploads file → API stores temp file, enqueues import job → worker parses (streaming), redacts, persists `http_transactions`, links to program/account tag → API reports result.
4. **Evidence:** upload via authenticated API → stored under `data/evidence/<uuid>/` (never static) → metadata + sha256 in DB → retrieval only through authenticated download endpoint.
5. **Report:** API renders from finding + linked evidence templates → Markdown/JSON/HTML artifact stored and downloadable.

## 4. Cross-Cutting Mechanisms

- **Correlation ID:** generated per HTTP request and per job; propagated through logs and tool-run records.
- **Redaction:** central `core/redaction.py` applied at log emission, tool-arg persistence, HAR import, report rendering.
- **Audit:** append-only audit table written by domain services (never by raw CRUD paths).
- **Time:** all timestamps UTC `timestamptz`.
- **Migrations:** Alembic; never auto-run against production data without backup (local app: compose runs `upgrade head` on boot).

## 5. Boundaries and Non-Functional Fit

- Single-user deployment ≈ low traffic; correctness and safety dominate over throughput.
- API sync endpoints (threadpool) are acceptable at this scale (ADR-001).
- All pure decision logic (scope, normalization, dedup, scoring, transitions) lives in `domain/` with zero I/O for testability (Constitution P9).

## 6. Key Risks & Residual (see ADRs / security.md)

- External tools cannot enforce per-request scope in all cases (e.g., nuclei redirects) → residual risk documented; mitigation = input filtering + no-follow flags + post-hoc violation logging (ADR-004, HF-SEC-005).
- DNS rebinding between policy check and tool request → mitigated where our code controls connections; documented residual risk for third-party tools (HF-SEC-015).
