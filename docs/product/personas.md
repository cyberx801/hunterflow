# HunterFlow — Personas

- **Version:** 0.1.0 (Draft, Phase 0)
- **Date:** 2026-10-29
- **Status:** Draft — pending approval gate G1

## P1 — Independent Bug Bounty Hunter (Primary)

- **Alias:** "Solo"
- **Context:** Runs 3–8 active programs simultaneously; part-time or full-time; works from a laptop; uses subfinder/httpx/nuclei, Burp Community or Caido, and scattered notes (Notion/plaintext).
- **Goals:**
  - Keep per-program context (scope, findings, tested hypotheses) across weeks-long engagements.
  - Know what was already tested and what changed since the last session.
  - Prioritize a growing pile of endpoints without losing good leads.
  - Write professional reports faster with reproducible evidence.
- **Pain points:**
  - Recon output is scattered across tool folders; re-running tools re-discovers the same assets.
  - No single answer to "what have I already tried?" — duplicated effort and missed leads.
  - Fear of accidentally testing out-of-scope assets (third-party deps, redirects, IP-only scope).
  - Report writing is manual assembly of screenshots, requests, and notes.
- **HunterFlow response:** Program-scoped workspace, normalized inventory, research cards, comparison view, finding lifecycle with evidence, Markdown/JSON report export.

## P2 — Web Application Penetration Tester (Primary)

- **Alias:** "Pentester"
- **Context:** Formal engagements with defined scope documents; evidence and reproducibility are contractual requirements; uses Burp Suite heavily.
- **Goals:**
  - Map scope rules faithfully (exact hosts, wildcards, exclusions, CIDRs) and test within them.
  - Document every test step and observation for the report.
  - Hand over a complete evidence package to the client.
- **Pain points:**
  - Scope interpretation errors during testing (redirects, third-party integrations).
  - Reconstructing test history for the report days after the engagement.
  - Splitting findings between Burp state, screenshots, and office documents.
- **HunterFlow response:** Versioned scope policy with enforcement, audit trail, HAR import from proxy sessions, evidence-linked findings, reproducible reproduction steps.

## P3 — API Security Researcher (Primary)

- **Alias:** "API Hunter"
- **Context:** Focuses on REST/GraphQL APIs; heavy multi-account testing (IDOR/BOLA, authn/authz); imports traffic from proxy or HAR files.
- **Goals:**
  - Inventory API endpoints with methods, parameters, and auth requirements.
  - Compare responses across two authorized test accounts systematically.
  - Track object-level authorization test hypotheses per endpoint.
- **Pain points:**
  - Manual diffing of responses between accounts in Burp Comparer (two items at a time).
  - Normalizing noise (timestamps, tokens) when comparing responses.
  - Keeping track of which endpoint was tested with which account pairs.
- **HunterFlow response:** Endpoint intelligence with auth indicators, HAR import, sanitized side-by-side comparison with diff highlighting and normalization rules, research cards for BOLA/IDOR hypotheses.

## P4 — Security Student (Secondary)

- **Alias:** "Learner"
- **Context:** Learning recon and web testing through CTFs, labs, and first sanctioned bug bounty attempts; budget-sensitive; needs guidance and structure.
- **Goals:** Follow a professional methodology; understand why a target deserves attention; learn report writing.
- **HunterFlow response:** Structured workflow, hypothesis templates/checklists, explainable prioritization, report templates, free and self-hosted.

## P5 — Security Engineer / Red Team (Secondary)

- **Alias:** "Engineer"
- **Context:** Runs authorized assessments of internal assets; automation-minded; values reproducibility, logs, and API access.
- **Goals:** Script against the platform; keep an inventory of internal assets; connect scanner output to actionable verification.
- **HunterFlow response:** REST API under `/api/v1`, job lifecycle, structured logs, deterministic core.

## P6 — Small Research Team (Secondary)

- **Alias:** "Team"
- **Context:** 2–5 researchers sharing a program; needs shared inventory and status visibility; avoids duplicate submissions.
- **Goals:** See what others already tested; coordinate findings; shared evidence store.
- **HunterFlow response (post-MVP evolution):** The single-user-first architecture must not preclude later multi-user support; v0.1.0 ships single-user only (see non-goals).
