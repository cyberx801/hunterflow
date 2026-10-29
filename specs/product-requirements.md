# HunterFlow — Product Requirements Specification (PRS)

- **Version:** 0.1.0 (Draft for G2)
- **Date:** 2026-10-29
- **Status:** Pending approval gate G2
- **Supersedes/extends:** `docs/product/*` (Phase 0), `specs/constitution.md` (G1, approved 2026-10-29)
- **Identifiers:** Functional `HF-FR-###` · Non-functional `HF-NFR-###` · Security `HF-SEC-###` · Privacy `HF-PRV-###` · Performance `HF-PER-###`. Priorities: **M**ust / **S**hould / **C**ould / **W**on't (this release).

---

## 1. Product Objectives

1. Give authorized researchers one persistent workspace for the full lifecycle: program → scope → recon → inventory → research → findings → evidence → report.
2. Make scope/authorization enforcement a system property, not a convention.
3. Preserve research continuity (discovered, tested, verified, rejected, planned).
4. Provide traceable evidence chains from asset to endpoint to test to finding.
5. Offer explainable prioritization without false confidence.
6. Remain fully functional self-hosted with no paid dependencies (Constitution P19).

## 2. Target Users

Per `docs/product/personas.md`: primary — P1 solo bounty hunter, P2 web pentester, P3 API security researcher; secondary — P4 student, P5 security engineer, P6 small team (post-MVP).

## 3. User Journeys (summary; details in `specs/design/user-flows.md`)

- **J1 — Onboarding:** install via Compose → create first account → land on empty Overview with functional empty states → create first program.
- **J2 — Set up a program:** define scope rules → validate with scope preview → save policy version.
- **J3 — Run recon:** pick profile → confirm effective scope → job runs in background with progress → results become inventory.
- **J4 — Investigate:** open endpoint → create research card from template → test (external) → record observations.
- **J5 — Compare accounts:** import HAR → pick two authorized-account transactions → compare with normalization → attach comparison to a research card.
- **J6 — Record a finding:** promote verified observation to finding → attach evidence → generate Markdown report.
- **J7 — Resume later:** open program → see "since last visit" changes, open research tasks, continue.

## 4. Functional Requirements

### Module A — Program & Scope (Milestone 2)

| ID | Requirement | Prio | Deps | Acceptance criteria |
|---|---|---|---|---|
| HF-FR-001 | Create program: name, platform (HackerOne/Bugcrowd/Intigriti/Other/custom), program URL, description, notes, policy source URL, last policy review date | M | — | Program appears in list; validation errors shown; audit event recorded |
| HF-FR-002 | Edit and archive program (archive hides it; data preserved) | M | HF-FR-001 | Archived programs filtered by default; can be re-enabled |
| HF-FR-003 | List programs: pagination, search by name, filter by platform | M | HF-FR-001 | ≤50 rows/page; search works |
| HF-FR-004 | Program workspace page: tabs (Scope, Assets, Endpoints, Research, Scans, Findings, Settings) | M | HF-FR-001 | All tabs render with data or functional empty states |
| HF-FR-005 | Scope rules CRUD: domain exact, domain wildcard (`*.example.com`, `*.example.com` + suffixes?), CIDR, URL/path restriction, HTTP method allow/deny, rate limits, automation permissions (crawl/scan allow/deny), notes | M | HF-FR-001 | Rules persist; invalid patterns rejected with clear errors |
| HF-FR-006 | Scope preview/validator: test candidate targets against effective policy; shows matching rule, decision, and whether confirmation is required | M | HF-FR-005 | Deterministic results matching unit-tested engine; exclusion precedence demonstrated |
| HF-FR-007 | Effective policy evaluation endpoint used by all outbound operations | M | HF-FR-005 | Every tool adapter consults policy before any request; unit-tested for wildcard/CIDR/exclusion cases |
| HF-FR-008 | Policy versioning: every rule change creates an immutable policy version; version list with diff view; history preserved | M | HF-FR-005 | Changing a rule creates new version; old jobs retain the version they ran under |
| HF-FR-009 | Ambiguous-target confirmation: targets that match only loosely (e.g., third-party dependency discovered) are flagged `requires_confirmation` and blocked until the user explicitly allows (one-time or rule) | M | HF-FR-007 | Out-of-scope target blocked with visible reason; explicit allow recorded in audit log |
| HF-FR-010 | Program notes (Markdown) with edit history | S | HF-FR-001 | Rendered markdown; version list |
| HF-FR-011 | Scope rule suggestions from policy text are **not** auto-applied (manual entry only in MVP) | W | — | n/a |

### Module B — Recon & Jobs (Milestone 2)

| ID | Requirement | Prio | Deps | Acceptance criteria |
|---|---|---|---|---|
| HF-FR-020 | Tool adapter registry with base interface: detect (path/version), build args (array only), parse output (JSONL), normalize to observations | M | — | Each adapter has unit + integration tests |
| HF-FR-021 | Tool availability & version detection shown in Settings | M | HF-FR-020 | Settings displays detected version or "missing" with install hint |
| HF-FR-022 | Scan profiles: `passive` (subfinder), `light_recon` (subfinder+httpx), `web_inventory` (+katana), `vuln_checks` (curated nuclei templates, explicit selection) | M | HF-FR-020 | Profile is a declarative ordered pipeline of tool steps; serializable |
| HF-FR-023 | Create scan job: program + profile + optional target subset (must be within scope) + dry-run flag | M | HF-FR-007 | Job created with policy version snapshot; invalid target rejected pre-queue |
| HF-FR-024 | Job lifecycle: `queued → running → completed/failed/cancelled`; progress (steps done/total); cancellation requested → tools killed → status `cancelled` | M | HF-FR-023 | Cancellation <5s to kill subprocess; status persisted across worker restart |
| HF-FR-025 | Execution history: scan jobs list with filters; per-job tool runs (tool, version, args, exit code, timing, output summary); raw output retrievable | M | HF-FR-024 | All fields persisted; args redacted of secrets |
| HF-FR-026 | Subprocess safety: argument arrays (never shell strings), timeouts, working-directory control, env allowlist, output size caps | M | HF-FR-020 | Injection test suite passes (see SEC) |
| HF-FR-027 | Concurrency & rate limits: max 1 concurrent scan per program (MVP), per-tool rate flags from policy | M | HF-FR-024 | Second job queues; rate flags appear in tool args |
| HF-FR-028 | Dry-run: job prints planned commands/steps without executing tools | M | HF-FR-023 | Dry-run completes without network activity (asserted in tests) |
| HF-FR-029 | Scope enforcement during execution: every discovered URL filtered through policy; redirects not followed out-of-scope (tool flags); violations logged as `blocked` | M | HF-FR-007 | E2E test with out-of-scope fixture shows blocked, not requested |
| HF-FR-030 | Output normalization: tool JSONL → typed observations with source tool_run id | M | HF-FR-020 | Parser unit tests for golden files |

### Module C — Asset & Endpoint Intelligence (Milestone 3)

| ID | Requirement | Prio | Deps | Acceptance criteria |
|---|---|---|---|---|
| HF-FR-040 | Asset model: domain, subdomain, ip, url, web_service, api_endpoint; normalized value + original value; first/last seen; scope status (in_scope/out_of_scope/needs_confirmation); http status; tech; tags; notes | M | HF-FR-030 | Persisted; scope status derived from policy engine |
| HF-FR-041 | Normalization & dedup: case, default ports, trailing slashes, equivalent URL forms → single canonical key per asset type | M | HF-FR-040 | Unit tests for equivalence classes; duplicate import creates no new asset |
| HF-FR-042 | Provenance: every asset links to discovery source (tool run / import job) and raw observation | M | HF-FR-030 | Raw observation JSON retrievable from asset |
| HF-FR-043 | Asset list: pagination, full-text search, filters (type, scope status, tags, source), sort, grouping by domain | M | HF-FR-040 | Query performance per HF-PER-001 |
| HF-FR-044 | Asset detail: metadata, related assets (parent/subdomain, resolved IPs), research cards, endpoints, history | S | HF-FR-040 | Renders without N+1 above budget |
| HF-FR-050 | Endpoint model: method, path, query params, content types, request body shape, auth indicators, status-code distribution, first/last seen | M | HF-FR-030 | Populated from katana + HAR import |
| HF-FR-051 | Endpoint categorization (auth, account, profile, admin, file, payment, object-access, resource-mgmt, api-versioning, other) — informational; manual correction allowed | M | HF-FR-050 | Categories visible as filter chips; user override persists |
| HF-FR-052 | Endpoint list/detail: filters (method, category, auth indicators, path pattern), research actions (create card, compare, add to findings) | M | HF-FR-050 | Actions navigate correctly |

### Module D — Research Workspace & Traffic (Milestone 4)

| ID | Requirement | Prio | Deps | Acceptance criteria |
|---|---|---|---|---|
| HF-FR-060 | Research card: hypothesis, related asset/endpoint (nullable), test category, required authorization, required test accounts, methodology, status, observations, notes, next action, timestamps | M | HF-FR-040/050 | CRUD persisted; card visible from asset/endpoint detail |
| HF-FR-061 | Statuses: Not Started, In Progress, Needs Verification, Confirmed, Rejected, Blocked, Archived; transitions validated (state machine) | M | HF-FR-060 | Invalid transitions rejected; history preserved |
| HF-FR-062 | Research templates & checklists: create template, instantiate on card; checklist items checkable | M | HF-FR-060 | Template instantiation copies items |
| HF-FR-063 | Card history & saved filters | S | HF-FR-060 | Filters persist per user |
| HF-FR-064 | Evidence linking to cards (link existing evidence or attach new) | M | HF-FR-060, HF-FR-090 | Linked evidence renders on card |
| HF-FR-070 | HAR import: validate, parse, sanitize (redaction), store as http_transactions linked to program + optional account tag | M | — | Malformed HAR rejected with error; valid HAR fully imported; count reported |
| HF-FR-071 | Burp/Caido interop via HAR export; document formats; no proprietary format parsing | S | HF-FR-070 | Docs describe export steps |
| HF-FR-072 | Traffic list: filter by host/path/method/status/source/account; detail view shows full sanitized request/response | M | HF-FR-070 | Rendering caps large bodies (truncation + expand) |
| HF-FR-073 | Comparison: select 2+ transactions; side-by-side method/URL/headers/query/body/status/headers/body/timing | M | HF-FR-072 | Synchronized scrolling; visual diff of changed lines |
| HF-FR-074 | Normalization rules: ignore configured headers (Date, Set-Cookie, Cache-Control…), normalize dynamic values (timestamps, UUIDs, nonces) via configurable regex/JSON-path rules | M | HF-FR-073 | Golden-file tests prove diff noise reduction |
| HF-FR-075 | Comparison sets persist (named), linkable to research cards/findings; explicit rule: status-code difference alone never auto-infers vulnerability; UI shows a review prompt instead | M | HF-FR-073 | Set reloadable; no auto-finding created |
| HF-FR-076 | Import redaction: default-redact Authorization/Cookie/Set-Cookie + custom patterns; redaction flag per transaction | M | HF-FR-070 | Imported data contains no tokens (tested) |

### Module E — Findings, Evidence, Reports (Milestone 5)

| ID | Requirement | Prio | Deps | Acceptance criteria |
|---|---|---|---|---|
| HF-FR-080 | Finding: title, description, category (OWASP/Web/CWE mapping), CWE, asset, endpoint, severity (CVSS-informational), confidence, impact, reproduction steps, status, validation status, discovery source | M | HF-FR-040 | CRUD; required fields validated |
| HF-FR-081 | Statuses: Potential, Under Investigation, Verified, False Positive, Duplicate, Report Ready, Reported, Resolved — with state machine + history | M | HF-FR-080 | Transitions validated; timestamps |
| HF-FR-082 | Separation of states: scanner observation, research hypothesis, finding are distinct entities — no interchangeable statuses | M | HF-FR-081 | Data model + API enforce distinct types |
| HF-FR-083 | Duplicate detection: deterministic matching (normalized endpoint + category + similarity threshold); candidate linking with provenance preserved (no destructive merge) | M | HF-FR-080 | Unit tests for matching; merge keeps both origins |
| HF-FR-084 | Severity & confidence fields; verified only via human confirmation (Constitution P4) | M | HF-FR-080 | API rejects auto-verified from scanner imports |
| HF-FR-090 | Evidence store: upload with type/size limits, sha256 integrity, download, delete, retention config; never publicly served | M | — | Upload rejects disallowed types/oversize; hash verified on download |
| HF-FR-091 | Evidence redaction UI (preview + apply patterns before storing) | S | HF-FR-090 | Redacted copy stored; original removable |
| HF-FR-100 | Report generator: Markdown, JSON, HTML; sections per Part 10 of master spec; verification status banner; no fabrication | M | HF-FR-080, HF-FR-090 | Generated report matches template; unverified finding labeled |
| HF-FR-101 | Report preview + export/download; auto-submission never offered | M | HF-FR-100 | Export works; no submission code path exists |
| HF-FR-102 | PDF export | W | — | Deferred |

### Module F — Prioritization (Milestone 5)

| ID | Requirement | Prio | Deps | Acceptance criteria |
|---|---|---|---|---|
| HF-FR-110 | Deterministic rule-based scoring: signals (new asset, new endpoint, auth-sensitive, unusual response, scanner observation, untested, recent change, researcher weight); explainable factor breakdown shown in UI | M | HF-FR-040/050 | Pure function; factors rendered; score changes explained |
| HF-FR-111 | Configurable weights (settings) with reset-to-default | S | HF-FR-110 | Weight change re-ranks; defaults documented |
| HF-FR-112 | Disclaimer rendered wherever scores shown: score is a lead indicator, not a vulnerability claim | M | HF-FR-110 | Present in UI + API docs |

### Module G — Platform (Milestone 1 & 6)

| ID | Requirement | Prio | Deps | Acceptance criteria |
|---|---|---|---|---|
| HF-FR-120 | Local authentication: create first account (setup flow), login, logout; Argon2id; session expiry; login rate limiting | M | — | SEC tests pass; lockout after N attempts |
| HF-FR-121 | CSRF protection + secure cookies (HttpOnly, SameSite) | M | HF-FR-120 | CSRF test passes |
| HF-FR-130 | Settings: tool availability/versions, evidence storage dir + size limits, retention, import redaction defaults, prioritization weights, display preferences | M | — | Settings persist; tool status reflects reality |
| HF-FR-140 | Audit log: auth events, policy changes, job events, finding transitions, evidence access — viewable, filterable, non-editable | M | — | Events recorded; tamper-evident (append-only API) |
| HF-FR-150 | REST API `/api/v1` with OpenAPI docs; async job resources; consistent error envelope; pagination/filter/sort | M | — | Docs at /docs; error shape consistent |
| HF-FR-160 | Docker Compose one-command install; volumes for DB + evidence; health checks | M | — | Fresh clone → running app ≤10 min |
| HF-FR-170 | Overview: programs, asset/endpoint counts, recent changes, active scans, research tasks needing action, findings needing verification, recent activity — real data only, no fake metrics | M | — | Empty state functional; counters query-efficient |
| HF-FR-180 | Light theme | C | — | Optional; dark is default |
| HF-FR-190 | Multi-user accounts | W | — | Post-MVP |
| HF-FR-200 | Scheduled monitoring (snapshots, change detection, opt-in notifications) | W (post-MVP M1) | — | Explicitly deferred per non-goals |

## 5. Non-Functional Requirements

| ID | Requirement | Acceptance criteria |
|---|---|---|
| HF-NFR-001 | Modular monolith + isolated workers (Constitution P7) | Deployment = 4 containers + optional demo |
| HF-NFR-002 | Type safety: typed backend (Pydantic) + TS frontend | CI type check gates merge |
| HF-NFR-003 | Deterministic core: scope match, normalize, dedup, scoring, transitions | Pure functions, no I/O, exhaustive tests |
| HF-NFR-004 | Error handling: classified errors, no silent failures | Error taxonomy documented; every caught error classified |
| HF-NFR-005 | Observability: structured logs + correlation IDs | Log line per request/job carries ID |
| HF-NFR-006 | Reproducibility: pinned deps, lockfiles, recorded tool versions/args | CI build from lockfile only |
| HF-NFR-007 | Accessibility: WCAG 2.2 AA where practical | Checklist in design specs; E2E a11y spot checks |
| HF-NFR-008 | Documentation: README quick start, dev setup, user docs, API docs | New contributor setup <30 min |
| HF-NFR-009 | Compatibility: Docker on Linux (primary), macOS, Windows (Docker Desktop) | CI matrix runs on Linux; compose validated |

## 6. Security Requirements

| ID | Requirement | Priority | Acceptance criteria |
|---|---|---|---|
| HF-SEC-001 | Argon2id password hashing, min 12-char policy, no plaintext secrets | M | Hash parameters verified in test |
| HF-SEC-002 | Session: opaque server-side token, expiry + renewal, logout invalidates; no JWT | M | Token not usable after logout/expiry |
| HF-SEC-003 | CSRF double-submit/sync token on all mutating requests | M | Test asserts reject without token |
| HF-SEC-004 | Scope enforcement precedes all active ops incl. redirects; violations blocked + logged | M | E2E out-of-scope fixture never hit |
| HF-SEC-005 | No out-of-scope redirect following in managed tools; documented residual risk where tool can't enforce | M | Tool flags configured; ADR documents gaps |
| HF-SEC-006 | SSRF defense for app-side fetches: loopback/private/link-local/metadata rejection, IP re-resolution, IPv4/IPv6 consistency | M | Test suite for each class |
| HF-SEC-007 | Secret redaction in logs, tool args, stored output, reports | M | Fixture with fake token appears redacted everywhere |
| HF-SEC-008 | Evidence never served statically; access via authenticated endpoint only | M | Direct URL fetch 404/403 |
| HF-SEC-009 | Upload validation: allowlist types, size caps, magic-byte check, non-executable storage | M | Polyglot/oversize rejected |
| HF-SEC-010 | Subprocess: arg arrays, no shell, env allowlist, timeout, no inherited creds | M | Command-injection test suite |
| HF-SEC-011 | Login/API rate limiting | M | Brute-force test throttled |
| HF-SEC-012 | Audit log append-only via API | M | Direct DB edit is the only bypass (documented) |
| HF-SEC-013 | CI: dependency vuln scan, secret scan, lockfile enforcement | M | CI pipeline configured |
| HF-SEC-014 | Containers non-root, minimal images, no docker socket, no privileged mode | M | Compose file reviewed per ADR-004 |
| HF-SEC-015 | DNS rebinding/TOCTOU mitigation for tool targets where feasible; residual risk documented | S | ADR-004/security.md states limits |

## 7. Privacy Requirements

| ID | Requirement | Priority |
|---|---|---|
| HF-PRV-001 | All data local; zero telemetry/phoning-home | M |
| HF-PRV-002 | Default redaction of auth tokens/cookies on import and in logs | M |
| HF-PRV-003 | Retention configuration for evidence and raw tool output | M |
| HF-PRV-004 | Export contains only user-selected data | M |

## 8. Performance Requirements (budgets to verify by benchmark, not claim)

| ID | Requirement | Target |
|---|---|---|
| HF-PER-001 | Asset/endpoint/finding list endpoints (paged 50) | p95 < 500 ms @ 10k rows, local hardware |
| HF-PER-002 | Overview page | < 2 s |
| HF-PER-003 | Job cancellation signal → process kill | < 5 s |
| HF-PER-004 | Tool hard timeout per step | default 10 min, configurable per tool |
| HF-PER-005 | Concurrent scans per program | 1 (MVP); global worker concurrency configurable |
| HF-PER-006 | Memory per worker process | < 512 MB typical; capped |

## 9. Explicit Exclusions (MVP)

Everything in `docs/product/non-goals.md` applies. Summarized: no proxy replacement, no engine reimplementation, no autonomous exploitation, no auto-submission, no multi-tenancy, no AI, no paid services, no continuous interception, no scheduled monitoring in v0.1.0.

## 10. Roadmap (post-MVP)

1. **v0.2 — Monitoring:** scheduled scans, snapshots, change detection, opt-in notifications.
2. **v0.3 — Intelligence:** local-AI assistant (Ollama, optional, off by default), hypothesis suggestions with source references.
3. **v0.4 — Collaboration:** multi-user, roles, shared programs.
4. Later: additional integrations, browser extension, graph visualization, PDF reports.

## 11. Traceability

Requirements map to problem statements: PS-1→HF-FR-040…052; PS-2→HF-FR-005…009, HF-SEC-004/005; PS-3→HF-FR-060…064; PS-4→HF-FR-070…076; PS-5→HF-FR-080…102; PS-6→HF-FR-110…112; PS-7→HF-FR-200 (post-MVP). Tasks in `specs/tasks.md` reference requirement IDs.
