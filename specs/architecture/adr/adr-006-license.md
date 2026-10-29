# ADR-006 — License: MIT

- **Status:** Proposed (G2, owner-approved Q2)
- **Date:** 2026-10-29

## Decision

HunterFlow is licensed MIT.

## Rationale

- Bundled/adapted tooling (ProjectDiscovery, nuclei-templates) is MIT; no copyleft obligations.
- MIT maximizes adoption and contribution, matching the security-tooling ecosystem the project lives in.
- GPL-3.0 components (e.g., Faraday) are excluded from any embedding; AGPL would deter corporate contributors without protecting anything we care about for v0.1.0.

## Consequences

- `LICENSE` at repo root; per-file attribution for vendored nuclei templates; license check in CI (MIT/Apache/BSD allowlist).
