# Changelog

All notable changes to HunterFlow are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

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

## [0.1.0] - 2026-10-29

Research Workspace MVP: programs and scope, recon orchestration, asset/endpoint inventory,
research workspace, HAR import and comparison, findings, evidence, reports, tests, docs.
