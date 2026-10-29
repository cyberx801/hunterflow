# Installation

## Requirements

- Docker 24+ and Docker Compose v2.
- 2 GB+ RAM recommended (the worker image includes the recon toolchain).
- No paid services or API keys are required.

## Steps

```bash
git clone https://github.com/your-org/hunterflow.git
cd hunterflow
cp .env.example .env
```

Edit `.env`:

| Variable | Purpose |
|---|---|
| `HF_SECRET_KEY` | **Required.** Session signing secret. Generate with `python -c "import secrets; print(secrets.token_urlsafe(48))"`. |
| `HF_BOOTSTRAP_USERNAME` / `HF_BOOTSTRAP_PASSWORD` | Optional: pre-create the first account. Otherwise use the first-run UI. |
| `HF_WEB_PORT` | Host port for the web UI (default 3000). |
| `HF_DB_PASSWORD` | PostgreSQL password (default `hunterflow`). |

Start:

```bash
docker compose up -d
docker compose ps
```

Open http://localhost:3000. The first-run flow creates your account (username + password, min 12 chars).

## What runs

| Service | Image | Notes |
|---|---|---|
| `web` | Next.js (standalone) | only host-exposed service |
| `api` | FastAPI | runs `alembic upgrade head` on boot |
| `worker` | same backend image | Dramatiq worker + pinned recon tools |
| `db` | postgres:16-alpine | internal only |
| `redis` | redis:7-alpine | job queue, internal only |
| `demo` | synthetic target | `--profile demo`, local tests only |

## Upgrading

```bash
git pull
docker compose build
docker compose up -d
```

Migrations apply automatically on API boot. Back up `pgdata` and the `evidence` volume before major upgrades (`pg_dump` + a tar of the evidence volume).

## Non-Docker local dev

See [development.md](development.md). Note: real (non-dry-run) scans require Redis + a worker process; local dev without these runs dry-runs synchronously.

## Security notes

- Only the `web` port is exposed to the host.
- Containers run non-root with `no-new-privileges`.
- Evidence is stored on a volume and only reachable through the authenticated download endpoint.
- Never expose HunterFlow directly to the public internet without an authn/authz reverse proxy and TLS.
