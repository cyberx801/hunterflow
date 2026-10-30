# Changelog

All notable changes to HunterFlow are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [0.6.0] - 2026-10-29

### Security
- Upgraded FastAPI 0.162 / Starlette 1.10 / uvicorn 0.54 (14 advisories cleared; pip-audit clean).
- Upgraded Next.js 16.4.3 / React 19.3 / zod 4.6.7 / @hookform/resolvers 6 / Playwright 1.64
  (npm audit clean).
- Added security headers on the API and web (nosniff, frame deny, referrer policy,
  permissions policy; HSTS in production). Disabled X-Powered-By.
- HF_LOGIN_RATE_LIMIT_PER_MINUTE is configurable (default 5) for automated tests.
- Migrated dynamic pages to Next 16 async params.

### Added
- Performance benchmarks for assets/endpoints/research/overview and cold-load frontend
  measurements (docs/benchmarks.md).
- Production checklist (docs/production-checklist.md).

### Changed
- Next config: poweredByHeader: false, optimizePackageImports for lucide-react.
- E2E can target an existing account via E2E_USER/E2E_PASSWORD.

## [0.5.0] - 2026-10-29

### Added
- Optional auto-created draft research cards for new endpoints and JS files, enabled per
  schedule (`auto_cards`). Cards are marked as auto-created, skip existing endpoint cards,
  and are capped per run.
- `web_crawl` profile (subfinder, dnsx, httpx, katana) for faster inventory without the
  passive URL step.

### Fixed
- Monitoring now commits miss-counter resets even when a run produces no change events.
- katana receives the container resolver (`/etc/resolv.conf`) so internal names resolve.
- Demo target is also reachable as `demo.example.com` (valid registrable domain for crawler
  scope).

## [0.4.0] - 2026-10-29

### Added
- Change detection now reports `changed_asset` (HTTP status and technology additions) and
  `new_js_file` events, with filters in the Monitoring UI.
- Optional page screenshots: build the worker with `WITH_SCREENSHOTS=1`
  (`HF_WITH_SCREENSHOTS=1`), enable `HF_SCREENSHOTS_ENABLED`, and run the Screenshots
  profile. Images are stored on the data volume and served through an authenticated
  endpoint; asset pages show the capture.

### Changed
- httpx targets are passed with `-u` (required for reliable screenshot output).
- Tool runs use a persistent `HOME`/`TMPDIR` under the data volume (needed for the
  headless browser and avoids noexec tmpfs).
- Recon httpx steps also include known in-scope URL assets (capped at 200).

## [0.3.0] - 2026-10-29

### Added
- PDF report export (reportlab) and an authenticated report download endpoint.
- Optional AI assistant over any OpenAI-compatible endpoint (local Ollama by default).
  Disabled unless `HF_AI_ENABLED=true`; reads only the workspace data on the open page,
  has no tool access, redacts secrets, and labels its output as advisory.
- Team workspace: multiple accounts sharing one workspace, `is_admin` role, admin user
  management (create, promote/demote, deactivate, reset password), optional open
  registration via `HF_ALLOW_REGISTRATION`.
- Settings tabs for team members and AI status; AI assist panels on research cards and
  findings; PDF buttons and report downloads in the UI.

### Changed
- Report format is stored as a string; `pdf` is accepted alongside markdown, json, html.

## [0.2.1] - 2026-10-29

### Added
- `dnsx` adapter: DNS resolution, stores IP assets and `resolves_to` relations.
- `gau` adapter: passive URL discovery from public sources; historical URLs are stored as
  URL assets and are not probed automatically.
- `url_discovery` scan profile (subfinder + gau). `light_recon` and `web_inventory` now
  include dnsx and gau.
- Per-step target files for tools that read a target list (`dnsx -l`).

### Changed
- Recon target shaping is tool-aware: `subfinder`, `dnsx` and `gau` receive hostnames;
  `httpx`, `katana` and `nuclei` receive URLs.

## [0.2.0] - 2026-10-29

### Added
- Continuous monitoring: scheduled scans per program with a dedicated scheduler process.
- Change detection: `new_asset`, `new_endpoint`, `possibly_removed_asset` and
  `removed_asset` events. Removals require two consecutive misses and only apply to asset
  types the scan profile can observe.
- Optional webhook notifications per schedule (`HF_WEBHOOK_URL`, Discord/Slack compatible).
- Monitoring page with schedules and a change feed.
- Server deployment guide and monitoring playbook.
- Sidebar labels are always visible on desktop.

### Changed
- Web UI binds to `127.0.0.1` by default (`HF_WEB_BIND` to override).
- Recon targets are shaped per tool: subfinder receives hostnames, httpx/katana receive URLs.
- Login rate limiting is per account (proxy-safe) in addition to a broader per-IP limit.

### Fixed
- Docker stack verified end to end (PostgreSQL, Redis, worker, scheduler, web, demo target).
- Dramatiq broker is configured in the API process as well, so enqueuing uses `HF_REDIS_URL`.
- Worker starts through the Dramatiq argument parser instead of passing a raw list.
- Tool arguments corrected against the installed binaries: katana targets via `-u`,
  katana `-disable-redirects`, httpx no invalid `-follow-redirects false`, nuclei `-dr`.
- Katana crawl scope regexes now match full URLs (they previously matched only hosts and
  filtered out the seed).
- Web image bakes the in-network API URL at build time (rewrites are evaluated at build).
- Data volume layout no longer conflicts with the worker tmpfs mounts.

## [0.1.0] - 2026-10-29

Research Workspace MVP: programs and scope, recon orchestration, asset/endpoint inventory,
research workspace, HAR import and comparison, findings, evidence, reports, tests, docs.
