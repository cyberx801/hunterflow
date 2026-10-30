# Performance benchmarks

Measured results only — no claims without measurement (constitution P15). Re-run with the
commands at the bottom.

Environment: local development machine, Docker Compose stack (PostgreSQL, Redis, worker,
scheduler, web), Chromium via Playwright, Next.js 16 production build.

## Backend list endpoints

`backend/scripts/benchmark.py` seeds 10,000 assets, 5,000 endpoints and 1,000 research cards,
then measures 100 authenticated requests per endpoint (p50/p95/p99, ms).

| Endpoint | p50 | p95 | p99 | Budget (p95 < 500 ms) |
|---|---|---|---|---|
| `GET /assets` (10k rows, page=50) | 35 ms | 41 ms | 74 ms | PASS |
| `GET /endpoints` (5k rows, page=50) | 24 ms | 29 ms | 47 ms | PASS |
| `GET /research` (1k rows, page=50) | 46 ms | 156 ms | 216 ms | PASS |
| `GET /overview` | 27–59 ms | 29–73 ms | 76–513 ms | PASS |

Notes:
- SQLite development database; PostgreSQL is the supported runtime and is expected to be
  comparable or faster. The CI job can run the same script against PostgreSQL.
- The earlier N+1 aggregation bug was fixed by batching counts and computing priority from
  cached signals (p95 dropped from ~770 ms to ~40 ms).

## Frontend page loads (cold cache)

Measured with Playwright, a fresh browser context per page, production build, `transferSize`
from the Resource Timing API. Local network, so TTFB is not representative of a real server;
JS transfer and load timing are the useful numbers.

| Page | TTFB | DOMContentLoaded | load | JS requests | JS transfer |
|---|---|---|---|---|---|
| /login | 10 ms | 67 ms | 145 ms | 8 | 189 KB |
| /overview | 10 ms | 34 ms | 144 ms | 9 | 199 KB |
| /assets | 12 ms | 35 ms | 146 ms | 9 | 198 KB |
| /findings | 11 ms | 35 ms | 166 ms | 10 | 242 KB |
| /research | 16 ms | 42 ms | 186 ms | 10 | 242 KB |
| /monitoring | 8 ms | 46 ms | 146 ms | 9 | 201 KB |
| /recon | 13 ms | 36 ms | 138 ms | 9 | 200 KB |

Production JS optimizations in place: route-level code splitting (Next App Router),
`optimizePackageImports` for `lucide-react`, `poweredByHeader: false`, gzip/brotli compression
by the Next server, no client-side source maps.

## Dependency security (same run)

| Check | Result |
|---|---|
| `uvx pip-audit -r requirements.txt` | no known vulnerabilities (FastAPI 0.162, Starlette 1.10, uvicorn 0.54) |
| `npm audit --omit=dev` | 0 vulnerabilities (Next 16.4.3, React 19.3, zod 4.6.7) |
| `pytest tests/security` | 31 passed |
| Security headers | API and web send `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`; HSTS in production |

## Re-run

```bash
cd backend && uv run python scripts/benchmark.py
cd web && node scripts/perf.cjs   # local measurement script used for this table
```

The frontend numbers are a point-in-time measurement, not a guarantee; re-measure after
dependency or bundle changes.

