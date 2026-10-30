# Deploying HunterFlow on a VPS

This is the beginner path: one small server, Docker Compose, and Caddy for automatic HTTPS.
Cloudflare is optional and covered at the end.

If you only want to use HunterFlow on your own machine, you do not need any of this — run
`docker compose up -d` locally and open http://localhost:3000.

## Do you need a server?

A server makes sense if you want:

- scheduled scans and monitoring to run while your laptop is off;
- access from other devices;
- a stable place for evidence and history.

A 2 vCPU / 2–4 GB RAM / 20–40 GB disk VPS is enough for one researcher. Hetzner, DigitalOcean,
Contabo or similar are fine.

## What you need

- A VPS running Ubuntu 22.04/24.04 with SSH access.
- A domain or subdomain (recommended, required for automatic HTTPS). A cheap domain is fine.
- About 15 minutes.

## 1. Point DNS at the server

At your DNS provider (or Cloudflare), create an `A` record:

```
hf.example.com  ->  <your server IPv4>
```

If you use Cloudflare, set the record to **DNS only** (grey cloud) for the first setup so
Caddy can obtain a certificate directly. You can enable the proxy later.

## 2. Install Docker on the server

```bash
ssh root@<server-ip>

apt-get update
apt-get install -y ca-certificates curl git
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
  > /etc/apt/sources.list.d/docker.list
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
```

Create a non-root user for the app (optional but recommended):

```bash
adduser hunter
usermod -aG docker hunter
su - hunter
```

## 3. Get the code and configure it

```bash
git clone https://github.com/cyberx801/hunterflow.git
cd hunterflow
cp .env.example .env
```

Edit `.env`:

```env
HF_SECRET_KEY=<paste output of: openssl rand -base64 48>
HF_DOMAIN=hf.example.com
HF_WEB_BIND=127.0.0.1
HF_ALLOW_REGISTRATION=false
# optional
HF_WEBHOOK_URL=
HF_WITH_SCREENSHOTS=0
```

Do not set `HF_WEB_BIND=0.0.0.0` when Caddy is in front.

## 4. Start it with Caddy

```bash
docker compose -f docker-compose.yml -f docker-compose.caddy.yml up -d
docker compose ps
docker compose logs -f caddy
```

Caddy will obtain a certificate for `HF_DOMAIN` on first start (ports 80/443 must be
reachable). Open `https://hf.example.com` and create the first account.

Then:

1. **Programs → New program**, add scope rules, publish a policy version.
2. **Recon → New scan** with a passive profile to check the pipeline.
3. **Monitoring → New schedule** for recurring scans (e.g. passive every 6 hours).

## 5. Firewall

Allow only SSH, HTTP and HTTPS:

```bash
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

Postgres and Redis are never published by the compose file.

## 6. Backups

```bash
mkdir -p ~/backups
docker compose exec -T db pg_dump -U hunterflow hunterflow | gzip > ~/backups/db-$(date +%F).sql.gz
docker run --rm -v hunterflow_evidence:/data -v ~/backups:/backup alpine \
  tar czf /backup/evidence-$(date +%F).tar.gz -C /data .
```

Add both lines to `crontab -e` (daily). Restore-test once into a scratch database.

## 7. Updating

```bash
cd ~/hunterflow
git pull
docker compose -f docker-compose.yml -f docker-compose.caddy.yml build
docker compose -f docker-compose.yml -f docker-compose.caddy.yml up -d
docker compose logs -f api
```

Take a database backup first. Migrations run on API start.

## 8. Cloudflare (optional)

You do not need Cloudflare. Caddy already gives you HTTPS. If you want Cloudflare for DNS,
DDoS protection or hiding the origin IP:

1. Keep the DNS record **proxied** (orange cloud) only after Caddy has issued a certificate.
2. SSL/TLS mode: **Full (strict)**. Never "Flexible" — the session cookie is `Secure` and
   login will break behind an HTTP origin.
3. Add a Cache Rule to **bypass cache** for `hf.example.com/api/*` and for HTML documents
   (`http.request.headers["accept"] contains "text/html"`). Next.js sets long-lived cache
   headers on static pages; bypassing avoids stale HTML.
4. Free-plan request body limit is 100 MB; HunterFlow caps HAR uploads at 50 MB, so this is
   fine.
5. WebSockets are not used by HunterFlow; no special setting is needed.

If you do not want to expose ports at all, an alternative is **Cloudflare Tunnel**
(`cloudflared`) or **Tailscale**; both are more moving parts than Caddy, so start simple.

## Troubleshooting

| Symptom | Check |
|---|---|
| Certificate not issued | DNS A record points to the server; ports 80/443 open; `docker compose logs caddy` |
| Login loops or cookie not set | You are on `http://`; use `https://`. Cookie is `Secure` |
| 502 Bad Gateway | `docker compose ps` — is `api` healthy? `docker compose logs api` |
| 413 on HAR upload | Proxy body limit; Caddy has none by default, Cloudflare free plan is 100 MB |
| Scans stay queued | `docker compose logs worker`; Redis must be healthy |
| Rate-limited logins | `HF_LOGIN_RATE_LIMIT_PER_MINUTE`; per-account default is 5/min |

Before going live, walk through `docs/production-checklist.md`.
