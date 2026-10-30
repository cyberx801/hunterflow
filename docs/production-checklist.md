# Production checklist

Use this before exposing an instance beyond your own machine.

## 1. Secrets and configuration

- [ ] `HF_SECRET_KEY` is a long random value, unique to this deployment.
- [ ] `.env` is not committed and is readable only by the deploy user.
- [ ] `HF_ALLOW_REGISTRATION=false` unless you intend open signup.
- [ ] `HF_AI_ENABLED` is `false` unless you have a reachable endpoint you trust.
- [ ] `HF_LOGIN_RATE_LIMIT_PER_MINUTE` is left at the default in production.
- [ ] Database password (`HF_DB_PASSWORD`) changed from the default.

## 2. Network and TLS

- [ ] `HF_WEB_BIND=127.0.0.1` (default) and a TLS reverse proxy in front.
- [ ] Only 22/80/443 are reachable; Postgres and Redis are not published.
- [ ] The proxy forwards `X-Forwarded-Proto` and sets a request size limit
      (`client_max_body_size 60m` if you import HARs).
- [ ] HSTS is enabled at the proxy (the API also sends it when `HF_ENV=production`).
- [ ] Login works over HTTPS. It will not over plain HTTP because the session cookie is
      `Secure`.

## 3. Container hardening

- [ ] Containers run non-root with `no-new-privileges` (compose default).
- [ ] `api`/`worker`/`scheduler` use a read-only root filesystem with `/tmp` tmpfs
      (compose default).
- [ ] The worker memory limit (1 GB) suits your scans; raise it for large crawls.
- [ ] No Docker socket is mounted into any container.

## 4. Data and recovery

- [ ] `pg_dump` backup scheduled and tested (restore into a scratch database).
- [ ] The `evidence` volume is backed up.
- [ ] Disk space monitored; screenshots and raw tool output live on the data volume.
- [ ] Retention expectations documented; evidence and raw output are not auto-pruned yet.

## 5. Security verification

- [ ] `pytest tests/security` passes.
- [ ] `pip-audit` and `npm audit` show no known vulnerabilities.
- [ ] Security headers present (`curl -I`).
- [ ] Login rate limiting and CSRF verified (log out and try a mutation without the token).
- [ ] Scope rules reviewed and a policy version published; scope preview behaves as expected.
- [ ] Only programs you are authorized to test are configured.

## 6. Operations

- [ ] Structured logs collected and rotated (Docker daemon logging or compose `logging`).
- [ ] Health checks green (`docker compose ps`).
- [ ] Scheduler runs as exactly one instance.
- [ ] Webhook notifications tested (if enabled).
- [ ] Upgrade procedure: `git pull`, `docker compose build`, `docker compose up -d`, watch
      `docker compose logs api`.
- [ ] A rollback plan exists (previous image tags or a database backup).

## 7. Monitoring and alerts

- [ ] Job failures are reviewed (`/recon` and the `job_failed` log lines).
- [ ] Disk, memory and API latency are watched.
- [ ] Scheduled scans use intervals appropriate to the program's rules and your reading
      capacity.

## 8. Known gaps at v0.6

- Single shared workspace (no per-user isolation).
- No automatic log rotation in the app.
- No CSP with nonces yet; the app sends the other hardening headers.
- Per-request redirect control inside third-party tools is limited (see
  `specs/architecture/security.md` §9).
