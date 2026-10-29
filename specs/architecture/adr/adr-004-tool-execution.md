# ADR-004 — Tool Execution Model

- **Status:** Proposed (G2)
- **Date:** 2026-10-29

## Decision

External tools run as subprocesses inside the worker container, from pinned binaries shipped in the worker image. Argument arrays only; no shell; env allowlist; per-run tmp working dirs; timeouts; process-group kill.

## Options

1. **Container-per-scan (DinD/DoD):** strongest isolation, but requires Docker socket or privileged daemon — violates Constitution P14 spirit and adds heavy operational risk.
2. **Host-installed tools:** zero isolation guarantees; version drift; not reproducible.
3. **Bundled subprocess in worker container** (chosen): reproducible pinned versions, no socket, adequate isolation via non-root + no-new-privileges + resource caps.

## Consequences

- Tools are Go binaries with modest footprints; worker image stays manageable.
- Residual risk: a malicious/compromised tool could read worker env/files; mitigated by non-root + read-only fs + tmpfs runs + no secrets in worker env beyond what the job needs.
- Per-request scope control inside tools is limited (documented per-tool in integrations.md).
