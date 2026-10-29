# HunterFlow — Deployment Architecture

- **Version:** 0.1.0 (Draft for G2) · Single-host Docker Compose, self-hosted only.

## 1. Services (compose)

| Service | Image | Exposed | Notes |
|---|---|---|---|
| `web` | built from `web/Dockerfile` (Next standalone) | **3000 → host 3000** | Only host-facing service |
| `api` | `backend/Dockerfile` | internal 8000 | `/healthz`, `/readyz` |
| `worker` | same backend image, entrypoint `dramatiq` | none | non-root, resource-capped |
| `db` | postgres:16-alpine | internal only | volume `pgdata` |
| `redis` | redis:7-alpine | internal only | no persistence needed for queue; AOF off |
| `demo` (profile `demo`) | demo vulnerable app | internal 8080 | tests + local demos only |

Networks: `internal` (web→api, api/worker→db/redis); web proxies `/api/*` → `api:8000`. DB/Redis reachable only from api/worker.

## 2. Configuration

- `.env.example` (committed): `HF_SECRET_KEY`, `HF_DB_URL`, `HF_REDIS_URL`, `HF_DATA_DIR`, `HF_MAX_EVIDENCE_MB`, optional tool flags. No real secrets committed (Constitution P14).
- Volumes: `pgdata`, `evidence` (`data/evidence`), `runs` (tmpfs in worker).
- One command: `docker compose up -d` → migrations run in api entrypoint (`alembic upgrade head`), first-run account creation flow in UI.

## 3. Environments

- **dev:** hot-reload api/web mounts; `demo` profile brings the synthetic target app.
- **prod (local):** built images, `HF_ENV=production`, docs endpoint disabled, stricter cookie flags.
- **CI:** compose file validated; images built in CI (GitHub Actions).

## 4. Backups & Data

- `pgdata` volume + `evidence` dir are the only persistent state; documented backup = `pg_dump` + tar of evidence.
- Migration safety: schema changes only forward; backup note in release checklist.

## 5. Hardening Summary

non-root containers, `no-new-privileges`, read-only root where possible, no docker socket mounts, no host network, minimal base images, health checks on all services (see security.md §5).
