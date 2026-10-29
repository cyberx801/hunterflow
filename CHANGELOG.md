# Changelog

All notable changes to HunterFlow are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

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
