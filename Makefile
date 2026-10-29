.PHONY: up down build logs test test-backend test-frontend test-e2e lint fmt db-upgrade db-revision

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

test:
	cd backend && uv run pytest

test-backend:
	cd backend && uv run pytest

test-frontend:
	cd web && npm run test --if-present && npm run lint

test-e2e:
	cd web && npx playwright test

lint:
	cd backend && uv run ruff check app tests
	cd web && npm run lint

fmt:
	cd backend && uv run ruff format app tests

db-upgrade:
	cd backend && uv run alembic upgrade head

db-revision:
	cd backend && uv run alembic revision --autogenerate -m "revision"
