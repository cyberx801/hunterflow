# Running HunterFlow on a server

HunterFlow is single-user and designed to sit behind a TLS reverse proxy on a small VPS.
This page covers the parts that matter on a server: persistence, restart behaviour, the
scheduler, backups and exposure.

## Sizing

- 2 vCPU, 2–4 GB RAM, 20–40 GB disk is comfortable for one researcher.
- The worker container is capped at 1 GB and the scheduler at 256 MB.
- Outbound internet is needed for passive recon sources and (optionally) webhooks.

## Exposure

The compose file binds the web UI to `127.0.0.1` by default:

```
HF_WEB_BIND=127.0.0.1
HF_WEB_PORT=3000
```

Only ports 80/443 (reverse proxy) and 22 (SSH) should be open in the firewall. Postgres and
Redis are internal-only and must never be published.

Do not expose the UI over plain HTTP on the internet. In production the session cookie is
`Secure`, so it will not be sent over HTTP and login will fail. Put TLS in front.

### Caddy (simplest)

```
hunter.example.com {
    reverse_proxy 127.0.0.1:3000
}
```

### Nginx

```nginx
server {
    listen 443 ssl;
    server_name hunter.example.com;

    ssl_certificate     /etc/letsencrypt/live/hunter.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/hunter.example.com/privkey.pem;

    client_max_body_size 60m;   # HAR / evidence uploads

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }
}
```

## Services and restarts

The compose file sets `restart: unless-stopped` on every service, so the stack comes back
after a reboot or a crash:

| Service | Role |
|---|---|
| `api` | HTTP API, applies migrations on boot |
| `worker` | runs scan jobs |
| `scheduler` | every 45 s, enqueues due scheduled scans |
| `web` | UI |
| `db`, `redis` | internal state |

Run the scheduler as exactly one instance. It is intentionally simple: `next_run_at` in the
database is the source of truth, and it advances the schedule before enqueuing.

## Continuous monitoring

1. Open **Monitoring → New schedule**.
2. Pick the program, a profile (start with `passive` every 6–12 hours), and the interval.
3. Leave notifications on if you want a webhook.

Each run is a normal scan job: it is validated against the program's scope policy, and it
appears in Recon history. After it finishes, HunterFlow records:

- `new_asset` / `new_endpoint` for things first seen in that run,
- `possibly_removed_asset` after one miss,
- `removed_asset` after two consecutive misses.

Removals are only considered for asset types the profile can actually observe, so a passive
scan never marks a URL as gone.

### Webhook notifications

Set one of these in `.env` and restart:

```env
HF_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

Discord and Slack incoming webhooks both work (the payload includes `content` and `text`).
Notifications are opt-in per schedule and are skipped silently if the URL is not set. The
webhook URL lives only in the environment, not in the database.

## Team workspace

The first account is the administrator. Admins manage users in the UI. To allow
self-registration, set:

```env
HF_ALLOW_REGISTRATION=true
```

All members share the same workspace; there is no per-user isolation.

## Optional AI assistant

Disabled by default. It talks to any OpenAI-compatible endpoint, so a local model is
enough:

```env
HF_AI_ENABLED=true
HF_AI_BASE_URL=http://host.docker.internal:11434/v1   # local Ollama
HF_AI_MODEL=llama3.1:8b
HF_AI_API_KEY=                                        # only if your endpoint needs one
```

The container already resolves `host.docker.internal` (compose adds the host-gateway
entry). If the endpoint is unreachable the assistant returns an error; the rest of the
application is unaffected. No paid API is required.

## Optional screenshots

The default worker image has no browser. To enable screenshots, build the worker with the
screenshot argument and enable the feature:

```env
HF_WITH_SCREENSHOTS=1
```

```bash
docker compose build worker
docker compose up -d worker api
```

This installs Debian's Chromium in the worker image (about 1 GB larger). The Screenshots
profile then captures in-scope pages; PNGs are stored on the data volume and served only
through the authenticated asset endpoint. `HF_SCREENSHOTS_ENABLED` is derived from
`HF_WITH_SCREENSHOTS` in the compose file.



## Troubleshooting

**Image pulls fail with `httpReadSeeker ... EOF` from CloudFront.**
Some networks cannot finish large Docker Hub layer downloads. Pull the same official image
from Google's mirror and tag it locally:

```bash
docker pull mirror.gcr.io/library/redis:7-alpine
docker tag  mirror.gcr.io/library/redis:7-alpine redis:7-alpine

docker pull mirror.gcr.io/library/postgres:16-alpine
docker tag  mirror.gcr.io/library/postgres:16-alpine postgres:16-alpine

docker pull mirror.gcr.io/library/python:3.12-slim
docker tag  mirror.gcr.io/library/python:3.12-slim python:3.12-slim

docker pull mirror.gcr.io/library/node:20-alpine
docker tag  mirror.gcr.io/library/node:20-alpine node:20-alpine
```

The backend image installs `uv` from PyPI, so `ghcr.io` access is not required.

**Worker stays `queued`.** Check `docker compose logs worker`; the broker must point at Redis
(`HF_REDIS_URL` and `REDIS_URL` are both set in compose).

**Login does not stick behind a proxy.** In production the session cookie is `Secure`; serve
the UI over HTTPS.

**A schedule did not run.** Confirm exactly one `scheduler` container is up and that the
program has at least one scope rule (scans with an empty policy are rejected).

## Backups

Only two things hold state: the Postgres volume and the evidence volume.

```bash
# database
docker compose exec -T db pg_dump -U hunterflow hunterflow | gzip > hunterflow-$(date +%F).sql.gz

# evidence files
docker run --rm -v hunterflow_evidence:/data -v "$PWD":/backup alpine \
  tar czf /backup/evidence-$(date +%F).tar.gz -C /data .
```

Test a restore before you need it. Migrations apply automatically on boot; take a backup
before upgrading.

## Upgrades

```bash
git pull
docker compose build
docker compose up -d
docker compose logs -f api
```

## Operating notes

- Logs are structured JSON in production (`docker compose logs api`). They are not rotated by
  Docker unless you configure `logging` in compose or the daemon.
- Failed jobs keep their classification in the job record (`TOOL_NOT_FOUND`, `TIMEOUT`, …).
- If a schedule is skipped because a scan is already running for that program, it retries in
  two minutes.
- Keep intervals sane and respect the program's rate limits. Do not schedule active profiles
  (crawling/checks) unless the program explicitly allows automated testing.
