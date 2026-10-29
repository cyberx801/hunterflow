# HunterFlow — Security Architecture

- **Version:** 0.1.0 (Draft for G2) · Implements Constitution P1–P5 and HF-SEC-*.

## 1. Authentication & Sessions

- **Argon2id** (argon2-cffi; m=64MB, t=3, p=1, 16-byte salt) for passwords; min length 12 (HF-SEC-001).
- **Server-side sessions** (ADR-007): 256-bit random token, stored hashed (SHA-256) in `sessions`; cookie `hf_session` = `HttpOnly; Secure; SameSite=Lax; Path=/`. Expiry 7 days + idle renewal; logout revokes row.
- **CSRF:** per-session `csrf_secret`; API returns `X-CSRF-Token` on session bootstrap; all mutating requests must present it; double-submit verify (HF-SEC-003).
- **Rate limiting:** login and token-verification endpoints limited (e.g., 5/min per IP, sliding window in Redis) (HF-SEC-011).
- First-run setup flow creates the initial user only when no user exists.

## 2. Authorization & Scope Enforcement (Constitution P2)

Layers, deliberately separated:

1. **Application authz:** authenticated user required for everything except login/health. (Single user in v0.1.0; per-entity ownership columns reserved.)
2. **Testing scope:** the policy engine (`domain/scope`) is the ONLY authority on what may be actively tested.

Enforcement points:
- **API pre-flight:** `POST /scans` validates target selection against the program's current policy version.
- **Worker per-target:** adapter pipelines filter every URL through `Policy.evaluate` immediately before execution; blocked targets are logged as `blocked` audit/observation rows, never executed.
- **Preview/dry-run:** same engine, zero network (HF-FR-028).
- **Redirects:** managed tools run with redirect-following disabled where the flag exists (katana/nuclei/httpx); redirect targets discovered passively are inserted as `needs_confirmation` assets, never auto-tested (HF-SEC-005). Residual risk: a tool following a redirect internally without our control is documented per-tool in integrations.md.
- **Ambiguity:** any target not covered by an explicit allow rule yields `requires_confirmation=true`; the user must record an explicit allow (one-time or rule) in the audit log before it can be tested (HF-FR-009).

## 3. SSRF & Network Safety (HF-SEC-006)

For any connection the application itself initiates (screenshots/tech probes via our code, none in MVP besides tool subprocesses):
- Reject loopback (127.0.0.0/8, ::1), RFC1918, link-local, ULA, CGNAT, multicast, unspecified, metadata endpoints (169.254.169.254, fd00:ec2::254) unless the program policy explicitly authorizes internal lab testing (opt-in flag per program).
- Resolve-then-connect with pinned IP for our connections; URL parser consistency checks (host casing, embedded credentials, backslash tricks, IPv4-in-IPv6).
- Imported URLs (HAR, findings) are data only — never fetched by the app.
- Explicitly-authorized internal lab testing is a per-program opt-in toggle; default off (distinguishes legitimate labs from accidental access).

## 4. Secrets & Redaction (HF-SEC-007)

- Secrets from environment only; `.env.example` documents keys; compose passes them to containers.
- Central `core/redaction.py`: patterns for bearer tokens, `Authorization`, `Cookie`, `Set-Cookie`, API-key-like strings; applied to: logs, tool-run `args`/output persistence, HAR import, report rendering, API error details.
- DB never stores raw auth tokens: HAR import redacts before persistence (HF-FR-076).
- CI secret scanning (gitleaks) + `.gitignore` guards.

## 5. Tool Execution Isolation (HF-SEC-010/014, ADR-004)

- Subprocess with argument arrays only — no shell, no concatenation; untrusted input (domains, paths) passes through the scope engine and validation regexes before arg construction.
- Environment allowlist (no inherited credential envs), explicit cwd under `/srv/hunterflow/runs/<job>/`, stdin closed.
- Timeouts (default 10 min/tool), output size caps (e.g., 50 MB), process-group kill on cancel.
- Worker container: non-root user, `no-new-privileges`, read-only root fs + tmpfs for run dirs, no docker socket, no privileged mode, resource limits via compose.
- Tool binaries ship in the worker image pinned to released versions with recorded checksums (ADR-004).

## 6. Evidence & Files (HF-SEC-008/009)

- Evidence stored outside web roots under `data/evidence/<uuid>/<sha256>`; download via authenticated endpoint with content-disposition; no static serving.
- Upload validation: extension+MIME+magic-byte allowlist (text, json, png, jpeg, gif, har, md, pdf, zip limited), size caps per type, stored non-executable (no-x bits, content sniff rejected).
- sha256 recorded at upload; verified on download; tampering detection surfaced in UI.

## 7. Supply Chain (HF-SEC-013)

- uv lockfile + package-lock.json committed; CI: `pip-audit`, `npm audit`, gitleaks, license check (MIT/Apache/BSD allowlist), Dependabot/renovate updates; minimal distroless-ish images, non-root.
- External tool downloads pinned to release artifacts with SHA256 recorded in `tools.lock`.

## 8. Audit & Honesty Controls (HF-SEC-012)

- Append-only audit API; events for: auth, policy edits/versions, ambiguity confirmations, job lifecycle, finding transitions, evidence access, settings changes.
- Data-state honesty: `observations` (raw), `research_cards` (hypotheses), `findings.validation_status` (human-verified only) are distinct tables/fields — no status can blur them (HF-FR-082).

## 9. Residual Risks (documented, per Constitution P2)

1. Third-party tools may internally follow redirects or resolve DNS after our check (TOCTOU); mitigated by no-follow flags + per-tool review; full elimination requires a proxy gateway — deferred, documented.
2. Passive DNS tools contact third-party resolvers; no active target traffic (acceptable under policy for passive profiles).
3. SQLite dev mode lacks row-level constraints parity; PostgreSQL is the only supported runtime.
