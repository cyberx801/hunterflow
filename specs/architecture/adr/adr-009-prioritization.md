# ADR-009 — Deterministic Rule-Based Prioritization First

- **Status:** Proposed (G2)
- **Date:** 2026-10-29

## Decision

v0.1.0 prioritization is a pure, deterministic scoring function over inventory state (new asset, new endpoint, auth-sensitive, unusual response, scanner observation, untested, recent change, researcher weight). No ML/AI in scoring.

## Rationale

- Constitution P9 (deterministic core) and P5 (honesty): scores must be explainable and reproducible.
- Rules are cheap to test exhaustively; every factor is displayed in the UI.
- Local AI (Ollama) may be added post-MVP as an optional, labeled, non-authoritative signal — never replacing the deterministic score.

## Consequences

- `domain/scoring` pure module with factor weights in settings (HF-FR-110/111).
- No model files, no GPU assumptions, no paid APIs.
