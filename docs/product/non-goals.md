# HunterFlow — Non-Goals

- **Version:** 0.1.0 (Draft, Phase 0)
- **Date:** 2026-10-29
- **Status:** Draft — pending approval gate G1

Non-goals are explicit decisions about what HunterFlow will **not** do. They protect the product's identity, safety posture, and maintainability. Each entry states the rationale and the condition under which it may be revisited.

## N1. No full proxy replacement

HunterFlow will not replace Burp Suite or Caido as an intercepting proxy, replay, or request-editing environment. Traffic enters via HAR/export import and selected stored requests.
- **Rationale:** Proxy engineering is a product of its own; interop via standard formats serves the workflow without duplicating mature tools.
- **Revisit if:** community demand and maintenance capacity justify a capture surface.

## N2. No reimplementation of scanning engines

HunterFlow will not reimplement subdomain enumeration, crawling, or vulnerability scanning engines. It orchestrates proven MIT/Apache-licensed tools (subfinder, httpx, katana, nuclei) as managed subprocesses.
- **Rationale:** These tools are better and more maintained than anything this project could build; the value is orchestration, normalization, and workflow.
- **Revisit if:** a concrete gap in existing tools is proven and scoped.

## N3. No autonomous exploitation

HunterFlow will never automatically exploit discovered weaknesses, perform credential attacks, bypass rate limits/WAFs/program restrictions, or run destructive tests. Potentially intrusive scanning requires separate, explicit approval and is excluded from the MVP.
- **Rationale:** Safety and legality; human-in-the-loop is a constitutional principle.
- **Revisit if:** never for autonomous exploitation; only curated, explicitly approved safe templates may be added.

## N4. No automatic vulnerability submission

HunterFlow will not submit findings to HackerOne, Bugcrowd, or any platform automatically.
- **Rationale:** Submissions are human legal acts requiring judgment; automation invites errors with real consequences.
- **Revisit if:** a strict draft-and-review flow with explicit per-finding confirmation is requested post-MVP.

## N5. No guaranteed vulnerability discovery

HunterFlow makes no promise that using it produces vulnerabilities. It organizes and prioritizes research work.
- **Rationale:** Honesty; scores and classifications are informational.

## N6. No enterprise multi-tenant SaaS

No multi-tenancy, RBAC tiers, SSO integrations, or SaaS hosting in v0.1.0. The architecture remains single-user-first but must not preclude later evolution.
- **Rationale:** Complexity budget; the primary persona is a solo researcher.
- **Revisit if:** after the core workflow is stable and tested.

## N7. No initial swarm of integrations

MVP ships a small, reliable set of tool adapters (subfinder, httpx, katana, nuclei) plus HAR import. Dozens of integrations are explicitly deferred.
- **Rationale:** Each adapter needs version detection, input validation, normalization, and tests; reliability over breadth.
- **Revisit if:** adapter framework proves low-cost after the first four.

## N8. No AI before deterministic workflows are reliable

No LLM features, no autonomous AI agents, no hosted commercial LLM dependency in MVP. A post-MVP local-AI assistant (Ollama, open-weight models) may summarize, suggest hypotheses, and draft from verified evidence — always with source references and human review, and never with autonomous access to testing tools.
- **Rationale:** Deterministic behavior and testability first; AI output must not fabricate endpoints, results, or vulnerabilities.
- **Revisit if:** post-MVP, optional and off by default.

## N9. No paid APIs, subscriptions, or cloud dependencies

No paid API calls, no commercial services required for any core function. Optional platform syncs (if ever added) must be opt-in with fallback.
- **Rationale:** Cost constraint and open-source ethos.

## N10. No continuous interception in MVP

Real-time traffic capture is deferred; MVP works with imported traffic and explicitly selected test requests.
- **Rationale:** Scope control; imported data is fully reviewable.
- **Revisit if:** a safe, bounded capture integration (e.g., opt-in proxy export) is designed post-MVP.

## N11. No distributed scanner fleets or advanced graph analysis

No multi-node scanning, no browser extension, no advanced graph/relationship visualization, no real-time collaboration in v0.1.0.
- **Rationale:** Out of scope for a maintainable first release.

## N12. No blockchain features

- **Rationale:** No user need exists; novelty for its own sake adds risk without value.
