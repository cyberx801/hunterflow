# HunterFlow — Backend Architecture

- **Version:** 0.1.0 (Draft for G2) · See ADR-001/002/003.

## 1. Stack

Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2 (sync) + psycopg3, Alembic, Dramatiq + Redis, structlog. Sync-style code throughout for contributor simplicity; FastAPI runs sync endpoints in the threadpool. Tool subprocesses run inside Dramatiq worker threads with dedicated supervision.

## 2. Layout

```
backend/
├── pyproject.toml / uv.lock
├── alembic/
├── app/
│   ├── main.py              # app factory; routers; middleware; health
│   ├── core/                # config, security(session/csrf), logging, errors, redaction, audit
│   ├── db/                  # engine, session, base, migration env
│   ├── schemas/             # Pydantic API models (v1 API contract)
│   ├── api/v1/              # routers: auth, programs, scopes, assets, endpoints,
│   │                        #           scans, jobs, research, traffic, comparisons,
│   │                        #           findings, evidence, reports, settings, overview, audit
│   ├── domain/              # PURE logic (no I/O):
│   │   ├── scope/           # policy engine: rules, matching, exclusions, CIDR
│   │   ├── assets/          # normalization + dedup keys
│   │   ├── endpoints/       # categorization, auth indicators
│   │   ├── dedup/           # finding duplicate scoring
│   │   ├── scoring/         # prioritization factors
│   │   └── state/           # card & finding state machines
│   ├── services/            # use-cases: program_service, scan_service, traffic_service,
│   │                        #   finding_service, evidence_service, report_service
│   ├── jobs/                # Dramatiq actors + pipeline runner + progress store
│   └── integrations/
│       ├── tools/           # base.py (Adapter protocol), subfinder.py, httpx.py,
│       │                    #   katana.py, nuclei.py, registry.py
│       └── parsers/         # tool JSONL → typed observations
└── tests/
    ├── unit/  integration/  security/  e2e/  fixtures/
```

## 3. API Design

- Prefix `/api/v1`; OpenAPI at `/docs` (disabled in production build by config).
- **Error envelope:** `{"error": {"code": "SCOPE_DENIED", "message": "...", "details": {...}, "correlation_id": "..."}}` with stable machine codes per error class.
- **Collections:** `page`/`page_size` (max 100), `q` (search), `filter[type]=…`, `sort=-last_seen`.
- **Jobs:** `POST /scans` → `202` + `{job_id}`; `GET /jobs/{id}` → status/progress; `POST /jobs/{id}/cancel`.
- **Auth:** `POST /auth/login|logout`, `GET /auth/me`; session cookie `hf_session`; CSRF header `X-CSRF-Token` verified on mutating requests.
- All request/response models typed in `schemas/`; response schemas are the contract consumed by the TS client.

## 4. Scope Engine (domain/scope)

```python
Rule(kind: "domain_exact"|"domain_wildcard"|"cidr"|"url_path"|"method"|"rate_limit"|"automation",
     value: str, effect: "allow"|"deny"|"restrict", priority: int, ...)
Policy(rules: list[Rule], version: int)
Decision(allowed: bool, requires_confirmation: bool, matched: list[Rule], reason: str)
```
- Evaluation order: exact denials → wildcard denials → exact allows → wildcard allows → CIDR; `url_path`/`method`/`automation` act as restrictors on top.
- `*.example.com` matches `a.example.com` but **not** `example.com` nor third-party `example.net` (explicit, tested).
- IP/CIDR: matched against resolved addresses when the client controls resolution; DNS names inside CIDR scope are handled by the documented residual-risk policy.
- Pure function: exhaustive pytest property tests.

## 5. Job Pipeline (jobs/)

- Actor `run_scan(job_id)`; pipeline = ordered steps from profile; per step: policy filter targets → adapter.run(args) with timeout/rate flags → parse → persist via services.
- **Progress:** step index + per-step counts into Redis key `job:{id}:progress`; API merges into `GET /jobs/{id}`.
- **Cancellation:** `cancel(job_id)` sets flag + `dramatiq-abort` signal; runner kills subprocess group and marks `cancelled` (ADR-010).
- **Retries:** per-step retry (max 2, exponential) for tool crashes; job-level `failed` with classified error code.
- **Idempotency:** dedup keys on assets/endpoints make re-ingestion safe; tool runs appended (append-only history).

## 6. Tool Adapter Protocol

```python
class ToolAdapter(Protocol):
    name: str
    def detect(self) -> ToolInfo | None          # path + version
    def build_args(self, ctx: StepContext) -> list[str]  # ARRAY ONLY
    def parse(self, stdout: bytes, ctx) -> Iterable[Observation]
```
- Registry maps tool name → adapter; adapters are the ONLY place tool binaries are referenced (Constitution P2).
- Every `build_args` result is redacted and persisted in `tool_runs.args`.

## 7. Testing (backend)

pytest + httpx TestClient + testcontainers/postgres fixture; pure domain tests need no infra; security suite in `tests/security/`; golden JSONL files in `tests/fixtures/tool-output/`.
