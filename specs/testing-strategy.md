# HunterFlow — Testing Strategy

- **Version:** 0.1.0 (Draft for G4) · Constitution P10: no feature without tests; never silently skip; never report unrun tests as passed.

## 1. Pyramid & Tooling

| Layer | Tool | Scope | Runs |
|---|---|---|---|
| Unit | pytest | pure domain logic + parsers + state machines | CI (fast) |
| Integration | pytest + testcontainers-postgres + redis | DB ops, API endpoints, job scheduling, worker execution, import/export, evidence storage, cancellation | CI |
| Security | pytest (adversarial suite) | see §4 | CI |
| E2E | Playwright | critical workflows F1–F7 | CI (compose profile) |
| A11y | axe-core in Playwright | spot-checks on key screens | CI |

Coverage policy: line coverage measured, not gamed; **domain/ (pure logic) ≥ 95%**, services/API ≥ 80%. Coverage gates merged only as CI checks on new code (no retroactive failures).

## 2. Unit Test Targets (Constitution P9)

- Scope matching: exact, wildcard, suffix rules, exclusions, precedence, CIDR (v4/v6), url_path/method/automation restrictors, `requires_confirmation` derivation — property-based where possible (hypothesis).
- URL normalization + dedup keys (case, ports, slash, fragments, IDN).
- HAR parser: valid, malformed, oversized entries, base64 handling.
- Dedup scoring: endpoint/category/similarity edge cases.
- Prioritization: factor computation, weight effects, explainability payload.
- State machines: cards, findings, jobs — legal/illegal transitions.
- Redaction patterns: tokens, cookies, keys in logs/args/bodies.
- Command-arg builders: input validation, injection attempts.

## 3. Integration Tests

- **API contract:** every `/api/v1` route happy-path + error envelope + auth/CSRF required (parameterized).
- **Job pipeline:** enqueue → worker executes fake adapter (no network) → status/progress/retry/cancel paths.
- **Import/export:** HAR import job, comparison-set persistence.
- **Evidence:** upload → hash → download → delete; size/type limits.
- **Migrations:** upgrade head on empty DB + data-preserving upgrade from prior revision fixture.
- **Tool adapters (real binaries, no external targets):** version detection + parsing of golden JSONL fixtures; `build_args` asserted for redaction and policy flags.

## 4. Security Test Suite

- Authn: wrong password, brute-force throttle, session expiry/revocation, cookie flags.
- CSRF: mutating endpoints reject missing token.
- Authz: unauthenticated access to all resources 401; cross-resource access rejected (future-proofing).
- Scope: out-of-scope targets blocked at API + worker; redirect-violation fixtures; `needs_confirmation` gating.
- SSRF: app-side fetch attempts to loopback/RFC1918/link-local/metadata rejected (incl. IPv6, decimal/hex IPs, host tricks).
- Command injection: hostile domain/path/param values through arg builders → no shell chars in argv; no execution.
- Data: HAR import with live tokens → stored redacted; logs/args contain no secrets.
- Files: polyglot/oversize uploads rejected; direct evidence URL 403/404.
- Honesty: API rejects auto-`verified` from scanner imports; report templates never assert unverified as verified.

## 5. E2E (Playwright, compose `demo` profile)

Journeys: F1 onboarding → F2 program+scope → F3 scan (demo profile, passive) → F4 research card → F5 HAR import + compare → F6 finding + evidence → F7 report export. Plus: keyboard-only F3/F4/F6; a11y spot checks; cancel-scan flow; error states (tool missing).

## 6. Fixtures & Demo Environment

- **`demo/` synthetic target app** (in-repo, clearly labeled): normal + authenticated endpoints, two test roles, harmless authorization inconsistencies (resource A readable by role B — by design), known expected results, no real vulnerability claims.
- Tool-output golden files in `backend/tests/fixtures/tool-output/*.jsonl`.
- HAR fixtures with embedded fake tokens for redaction tests.
- **No automated test ever touches third-party or production systems.**

## 7. Running & Reporting

- `make test` (all layers), `make test-unit`, `make test-sec`, `make test-e2e`.
- CI reports per-layer; unexecutable tests are marked skipped with reasons and reported — never silently dropped.
