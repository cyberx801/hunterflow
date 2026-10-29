# Contributing to HunterFlow

Thanks for your interest in contributing. HunterFlow is a self-hosted research workspace for authorized security testing. Please read the [Code of Conduct](CODE_OF_CONDUCT.md) and [SECURITY.md](SECURITY.md) first.

## Ground rules

- **Authorization first.** HunterFlow must never help test targets without authorization. Contributions must not weaken scope enforcement, add autonomous exploitation, or bypass program restrictions.
- **No fabricated claims.** Tests must actually run and pass. Demos using synthetic fixtures must say so.
- **Spec-driven.** Behavior changes start from `specs/` documents; a PR that changes behavior should update the relevant spec, task, or decision log in the same change set.
- **Tests required.** No behavior change without tests (see `specs/testing-strategy.md`).

## Development setup

1. Clone, then `docker compose up -d` (or see `docs/development.md` for non-Docker dev setup).
2. Backend: `cd backend && uv sync && uv run pytest`.
3. Frontend: `cd web && npm install && npm run dev`.
4. E2E: `cd web && npx playwright test`.

## Pull requests

- Branch from `main`; conventional commit messages with a module scope (e.g., `feat(scope): …`).
- CI must be green: lint, typecheck, unit, integration, security, E2E.
- Keep changes focused; one concern per PR.
- New tool adapters must follow `specs/architecture/integrations.md` and include golden-file fixtures.

## Adding a nuclei template

Templates are curated per the constitution (human oversight for security testing). Open an issue proposing the template, its category, and why it is safe; do not add templates directly.

## Questions

Open a discussion or issue. For security matters use the process in [SECURITY.md](SECURITY.md).
