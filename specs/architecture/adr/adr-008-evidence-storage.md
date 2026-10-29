# ADR-008 — Evidence on Filesystem + DB Metadata

- **Status:** Proposed (G2)
- **Date:** 2026-10-29

## Decision

Evidence files stored on disk under `data/evidence/<uuid>/<sha256>` with DB rows holding metadata, hashes, and links. Tool outputs similar (`data/runs/`). No blobs in Postgres.

## Rationale

- Evidence can be large (screenshots, HAR, bodies); blobs bloat the DB and complicate backups.
- Filesystem + sha256 gives straightforward integrity checks and easy file-level retention/deletion.
- Backups: pg_dump + tar of `data/` (documented in deployment.md).

## Consequences

- Evidence endpoint streams files after auth check; never static-served (HF-SEC-008).
- Atomic writes (tmp + rename) and hash verification on read.
