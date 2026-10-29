# HunterFlow — Project Constitution

- **Version:** 0.1.0
- **Status:** Draft — pending human approval at gate **G1**
- **Date:** 2026-10-29
- **Normative keywords:** This document uses the RFC 2119 meanings: **MUST**, **MUST NOT**, **SHOULD**, **MAY**.

---

## 1. Purpose

This constitution is the highest-level engineering law of the HunterFlow project. It defines the mission, the mandatory engineering principles, and the process for changing them. Every design document, implementation task, and review MUST be consistent with this document. Where a lower-level document conflicts with the constitution, the constitution wins until formally amended.

## 2. Mission

**Help authorized security researchers move efficiently from reconnaissance to structured investigation and evidence-backed reporting.**

HunterFlow is a research assistant and workflow system. It is not an autonomous exploitation platform.

## 3. Mandatory vs. Recommended

- Principles marked **MUST** are binding constraints. No implementation may knowingly violate them; exceptions require a constitutional amendment.
- Principles marked **SHOULD** are strong recommendations; deviations are permitted with a documented rationale in an ADR or decision log.
- Principles marked **MAY** are options the project may adopt when justified.

## 4. Principles

### P1 — Security by default (MUST)

- The system MUST be secure in its default configuration: authenticated access, safe session handling, secure cookies, CSRF protection where applicable, and secret-free configuration.
- Any feature that performs active network operations MUST be gated by an explicit authorization policy (see P2).
- Security-relevant code (auth, scope enforcement, file handling, serialization, subprocess execution) MUST have dedicated tests, including adversarial tests.

### P2 — Authorization and scope enforcement (MUST)

- Every active outbound testing operation MUST pass through a centralized, versioned execution-policy engine bound to a program's scope before any network request is made.
- Scope matching MUST support exact hosts, wildcards, exclusions with defined precedence, IP/CIDR rules, and must reject anything not covered by the effective policy.
- Out-of-scope redirects MUST NOT be followed by managed tools; discovered third-party assets MUST be marked out-of-scope by default.
- Ambiguous authorization MUST require explicit manual confirmation; a language-model interpretation MUST NOT be the sole authorization decision.
- The system MUST document residual risks where external tools cannot provide per-request control.
- NEVER assume a discovered asset is authorized for active testing.

### P3 — Privacy and sensitive data handling (MUST)

- The system MUST NOT store raw authentication tokens, session cookies, or credentials unless the user explicitly requires it and confirms the risk.
- Evidence MUST be sanitized/redacted where configurable; sensitive evidence MUST NOT be publicly accessible by default.
- Logs and reports MUST redact secrets (API keys, tokens, cookies) via a central redaction mechanism.
- The application itself MUST resist SSRF from imported data (loopback, private ranges, link-local, metadata endpoints, DNS rebinding, IPv4/IPv6 inconsistencies).

### P4 — Human oversight for security testing (MUST)

- Potentially intrusive testing MUST NOT be automated. Vulnerability *checks* in the MVP are limited to explicitly selected, curated, safe templates.
- Verification of any finding MUST be performed or confirmed by a human before the system may label it "Verified".
- The system MUST NEVER automatically submit findings to bug bounty platforms.

### P5 — Honesty and non-fabrication (MUST)

- The system MUST distinguish observation vs. hypothesis vs. manually verified vulnerability as distinct data states.
- An unverified observation MUST NOT be presented as a confirmed vulnerability.
- Reports MUST clearly state the verification status of every finding.
- No feature may fabricate tool results, evidence, or implementation status — including documentation and demos. Demo environments using synthetic fixtures MUST be labeled as such.

### P6 — API-first design (MUST)

- All functionality MUST be exposed through a versioned REST API under `/api/v1`.
- The API MUST ship OpenAPI documentation, typed request/response models, consistent error shapes, pagination, and filtering/sorting for collections.
- Long-running operations MUST be exposed as asynchronous job resources; HTTP requests MUST NOT be held open while scanning.

### P7 — Modular architecture (MUST)

- The system MUST be a modular monolith with isolated background worker processes. Microservices MUST NOT be introduced without a justified ADR approved by the human.
- Components MUST communicate through typed interfaces; tool integrations MUST be isolated behind adapter interfaces so integrations cannot bypass the scope policy.
- The database MUST NOT be designed around raw scanner JSON; source observations MUST be stored separately from normalized entities with provenance.

### P8 — Type safety and static verification (MUST)

- Backend code MUST be typed (Pydantic models for all API boundaries; typed SQLAlchemy models).
- Frontend code MUST be TypeScript; API contracts SHOULD be shared or generated from the backend schema (Zod mirrors of request/response types).
- CI MUST run type checking and treat failures as build failures.

### P9 — Deterministic core behavior (MUST)

- Scope matching, URL normalization, deduplication, prioritization scoring, and state transitions MUST be pure, deterministic functions with exhaustive unit tests.
- Randomized behavior, if any, MUST be explicit, seeded when possible, and isolated from the core pipeline.

### P10 — Test-driven verification (MUST)

- Unit, integration, security, and end-to-end tests are mandatory per the testing strategy (`specs/testing-strategy.md`).
- A feature is not "done" without its tests. Tests MUST NOT be skipped silently; a test that cannot run MUST be reported as "not executed".
- CI MUST fail on failing tests.

### P11 — Explicit error handling (MUST)

- Errors MUST be classified and handled explicitly: no silent swallowing, no bare `except`, no unchecked subprocess failures.
- Job failures MUST carry failure classification, bounded retries with backoff, and user-visible status.

### P12 — Observability (MUST core / SHOULD breadth)

- The system MUST emit structured application logs with correlation IDs for requests and jobs.
- Job lifecycle (status, progress, cancellation, history) MUST be persisted and visible in the UI.
- The system SHOULD expose basic operational metrics; Prometheus-compatible metrics MAY come post-MVP.

### P13 — Reproducibility (MUST)

- Tool executions MUST record tool name, version, arguments, and output so results can be reproduced.
- Dependencies MUST be pinned with lockfiles; the environment MUST be reproducible via Docker Compose.
- Migrations MUST be versioned (Alembic) and reversible where practical.

### P14 — Dependency management and supply chain (MUST)

- Dependencies MUST be pinned and reviewed before addition. Provenance, license, and maintenance status MUST be verified before adoption.
- CI MUST run dependency vulnerability scanning and secret scanning. Secrets MUST NEVER be committed; `.env.example` documents required variables.
- Container images MUST be minimal; privileged containers and unrestricted Docker socket access MUST NOT be used.

### P15 — Performance budgets (SHOULD)

- Core screens SHOULD meet documented performance targets (e.g., list endpoints return within defined budgets with pagination; dashboards must not render unbounded data).
- Performance claims MUST NOT be made without benchmarks; the implemented system MUST be benchmarked before results are documented.

### P16 — Accessibility (SHOULD)

- The UI SHOULD target WCAG 2.2 AA: keyboard navigation, visible focus, semantic controls, adequate contrast, screen-reader labels, and reduced-motion support.

### P17 — Open-source maintainability (MUST)

- The repository MUST include README, LICENSE, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, CHANGELOG, `.env.example`, Docker Compose, CI, and issue/PR templates.
- Documentation MUST be updated in the same change set as behavior changes.
- Realistic screenshots only; no fabricated claims of features.

### P18 — Backward compatibility (SHOULD)

- API changes SHOULD preserve `/api/v1` stability within a major version; breaking changes require a version bump and documented migration.
- Database migrations MUST preserve existing user data.

### P19 — No paid external services (MUST)

- Core functionality MUST work without paid API calls, subscriptions, or commercial services. Optional integrations that require credentials MUST be opt-in and degrade gracefully.

### P20 — Single-user-first evolution (MUST)

- v0.1.0 MUST be single-user-first: authentication and application permissions are still separated conceptually (authn ≠ authz ≠ testing scope), but no multi-tenancy or RBAC complexity may enter the MVP.
- The architecture MUST NOT preclude a later multi-user evolution (users table, ownership columns on core entities MAY exist from day one if zero-cost).

## 5. Binding Architectural Constraints

Derived from the principles; mandatory unless amended:

1. **Stack:** Python 3.12+ / FastAPI / Pydantic / SQLAlchemy / Alembic backend; Next.js / TypeScript / Tailwind / shadcn-ui frontend; PostgreSQL primary database. Alternatives require an approved ADR.
2. **Workers:** Background jobs run in isolated worker processes (not in-process for long jobs), with scheduling, retries, cancellation, timeouts, concurrency limits, and progress reporting. Exact queue technology is decided at gate G2.
3. **Tool execution:** subprocess-only for external tools; argument arrays (never shell-string concatenation of untrusted input); timeouts; cancellation; controlled working directories; no implicit network privileges beyond policy.
4. **Scope engine:** a single authoritative scope/execution-policy service; all adapters MUST consult it.
5. **Data model:** normalized entities (programs, assets, endpoints, findings, evidence, …) with provenance; raw tool output stored separately.

## 6. Governance and Amendment Process

1. Any contributor may propose an amendment as a pull request against `specs/constitution.md` plus a rationale in `specs/decisions.md`.
2. The amendment MUST state what changes, why, and its impact on existing features and on the four approval gates (G1–G4).
3. **The human owner MUST explicitly approve the amendment in writing.** Silence is not approval. The AI MUST NOT record approval on the human's behalf.
4. Approved amendments bump the constitution version: major for principle changes, minor for clarifications.
5. All lower-level specs MUST be re-checked for consistency after an amendment.

## 7. Approval Gates

- **G1 — Constitution** (this document): requires explicit human approval before Phase 2 begins.
- **G2 — Product requirements + architecture:** explicit human approval of PRS and architecture documents before implementation design.
- **G3 — UI/UX design system:** explicit approval before full interface implementation.
- **G4 — Implementation plan:** explicit approval before feature implementation.
- Gates MUST be completed in order; each approval MUST be recorded by the human in `specs/decisions.md`.

## 8. Approval Record

| Gate | Document | Status | Approved by | Date |
|---|---|---|---|---|
| G1 | Constitution v0.1.0 | **APPROVED** | Project owner | 2026-10-29 |
| G2 | PRS + Architecture | Pending review | — | — |
| G3 | UI/UX design | Pending review | — | — |
| G4 | Implementation plan | Pending review | — | — |

**Note:** Approval records are maintained by the owner in `specs/decisions.md`; this table mirrors that log. The owner approved G1 in writing on 2026-10-29 ("all aproved continue").
