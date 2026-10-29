# ADR-007 — Server-Side Sessions (No JWT)

- **Status:** Proposed (G2)
- **Date:** 2026-10-29

## Decision

Opaque session tokens stored hashed in the DB with expiry/revocation; CSRF via per-session secret double-submit. No JWT.

## Rationale

- Single-user local app: instant revocation, simple expiry semantics, no token-storage XSS surface in the browser (HttpOnly cookie).
- JWTs add key management and revocation complexity with no benefit here; cookies already needed for CSRF-safe browser auth.

## Consequences

- `sessions` table; session cleanup job (expired rows) on startup + periodic.
- Future multi-user evolution reuses the same table.
