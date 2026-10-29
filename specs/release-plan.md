# HunterFlow — Release Plan

- **Version:** 0.1.0 (Draft for G4)

## 1. Versioning & Cadence

- **SemVer** for releases; `main` is always releasable; feature branches + PRs with CI gates.
- v0.1.0 = Research Workspace MVP (M1–M6). Post-MVP: v0.2 monitoring, v0.3 local AI, v0.4 collaboration (PRS §10).
- Pre-1.0 stability promise: `/api/v1` may break only with a minor bump and CHANGELOG entry; data migrations always forward-compatible.

## 2. Branch & PR Policy

- `main` protected: requires CI green (lint, type, unit, integration, security, E2E) + 1 review.
- Conventional commits; scopes per module (e.g., `feat(scope): …`, `fix(jobs): …`).
- No commits without tests touching behavior; docs updated in the same PR.

## 3. v0.1.0 Release Checklist

- [ ] M1–M6 Definition of Done verified in CI (never by assertion alone).
- [ ] Fresh-machine install test: clean clone → `docker compose up -d` → F1–F7 usable.
- [ ] Security suite + dependency scans green; no secrets in history (gitleaks full-scan).
- [ ] License + attributions (MIT; nuclei-templates curation note) present.
- [ ] README screenshots captured from the running app (not fabricated); demo labeled synthetic.
- [ ] CHANGELOG summarizing features, known limitations, and residual risks (security.md §9).
- [ ] Git tag `v0.1.0` signed; release notes drafted (no public deployment without owner approval).

## 4. Post-Release

- Watch issues/PRs; patch releases (v0.1.x) for bugs/security without new features.
- Maintain `SECURITY.md` disclosure path; no bounties (self-funded open source).
