# Development

## Backend (Python 3.12 + uv)

```bash
cd backend
uv sync --all-groups
uv run alembic upgrade head          # needs a database URL (SQLite dev default)
uv run uvicorn app.main:app --reload --port 8000
uv run python -m app.jobs.worker     # separate terminal; needs Redis (see below)
```

- Dev database defaults to SQLite (`hunterflow-dev.db`) when `HF_DATABASE_URL` is unset and `HF_ENV=development`. PostgreSQL is the supported runtime.
- For real scans locally, start Redis (e.g. `docker run -d -p 6379:6379 redis:7-alpine`) and set `HF_REDIS_URL`.

### Tests

```bash
uv run pytest                  # unit + integration + security (SQLite)
uv run pytest tests/unit       # fast pure-logic tests
uv run pytest tests/security   # adversarial suite
```

CI runs the same suite against PostgreSQL + Redis (see `.github/workflows/ci.yml`).

## Frontend (Node 20)

```bash
cd web
npm install
npm run dev                     # http://localhost:3000, proxies /api to :8000
npm run typecheck
npm run build
```

## End-to-end (Playwright)

```bash
# Start backend (port 8000) + web (port 3000) first, then:
cd web
npx playwright install chromium
npx playwright test e2e
```

README screenshots: `SCREENSHOTS=1 npx playwright test e2e/screenshots.spec.ts` writes real captures to `docs/screenshots/`.

## Demo target

The `demo/` app is a **synthetic, intentionally inconsistent** FastAPI service used only for local tests. Run it with `docker compose --profile demo up -d` or standalone:

```bash
cd demo && pip install -r requirements.txt && uvicorn app:app --port 8080
```

## Conventions

- Spec-driven: behavior changes start from `specs/`; see [CONTRIBUTING.md](../CONTRIBUTING.md).
- Tests are mandatory (project constitution P10). Never report a test as passed unless it ran.
- Conventional commits with a module scope (e.g. `feat(scope): …`).
