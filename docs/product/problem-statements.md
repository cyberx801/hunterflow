# HunterFlow — Problem Statements

- **Version:** 0.1.0 (Draft, Phase 0)
- **Date:** 2026-10-29
- **Status:** Draft — pending approval gate G1
- **Format:** Each problem lists affected personas, current state (verified against public docs 2026-10-29), existing workarounds, HunterFlow response, feasibility, and differentiation strength.

---

## PS-1: Fragmented, non-persistent recon results

- **Problem:** Reconnaissance output is scattered across per-tool file trees and terminal output. Re-running tools re-discovers known assets; there is no persistent, deduplicated, queryable inventory across sessions and programs.
- **Personas:** P1, P2, P3, P5.
- **Current state:** subfinder/httpx/katana/nuclei are stateless per-run (JSONL to stdout/files); reconFTW writes `Recon/<domain>/` folder trees; Amass keeps an opaque internal graph DB. None provides a normalized cross-program inventory with change history.
- **Workarounds:** Manual spreadsheets, `notify`-piped diffs, re-scanning, custom scripts.
- **HunterFlow response:** Normalized asset/endpoint inventory with discovery provenance, first-seen/last-seen, scope status, dedup across sources, and per-program views.
- **Feasibility:** High — pure backend data modeling + subprocess JSON ingestion (verified tool interfaces).
- **Differentiation:** High — verified gap in every examined tool.

## PS-2: Scope/authorization is tracked in the researcher's head

- **Problem:** Program scope (wildcards, exclusions, CIDRs, allowed testing methods) lives in policies and memory. Tools enforce only per-run filters; redirects and discovered third-party assets can silently move testing out of scope.
- **Personas:** P1, P2, P6.
- **Current state:** katana/nuclei support per-run scope flags; no examined tool maintains a versioned program policy that gates all outbound operations. HackerOne/Bugcrowd offer no anonymous scope API to automate ingestion.
- **Workarounds:** `inscope`/`.scope` files, manual checklist discipline.
- **HunterFlow response:** Centralized, versioned execution policy per program; scope validation service; enforcement before every active network operation; redirect validation; dry-run mode; policy change history; manual confirmation of ambiguous targets.
- **Feasibility:** Medium-High — deterministic matching logic is testable; residual risks (TOCTOU, DNS rebinding, per-request control limits of external tools) must be documented.
- **Differentiation:** High — foundational property, verified gap.

## PS-3: Research knowledge (hypotheses, tests, rejections) is lost between sessions

- **Problem:** The researcher's core work product — "I tested X on endpoint Y with accounts A/B and rejected it because Z" — lives in scattered notes or memory. Weeks later, context is lost; effort is duplicated; good leads are forgotten.
- **Personas:** P1, P2, P3.
- **Current state:** No examined tool models hypotheses or test outcomes. Burp/Caido keep session-bound histories; Faraday/DefectDojo start from findings, not investigations.
- **Workarounds:** Notion/OneNote/plaintext notes with manual cross-references.
- **HunterFlow response:** Research cards attached to assets/endpoints with hypothesis, methodology, status lifecycle (Not Started → Confirmed/Rejected/Blocked), observations, next actions, templates, and evidence links.
- **Feasibility:** High — CRUD + workflow state machine.
- **Differentiation:** Very high — this is HunterFlow's core identity.

## PS-4: Multi-account authorization testing is manual and error-prone

- **Problem:** BOLA/IDOR and authz testing requires comparing responses across authorized test accounts. Manual diffing (Burp Comparer: two items, manual) plus noisy dynamic content (timestamps, tokens) makes systematic comparison tedious.
- **Personas:** P3, P1, P2.
- **Current state:** Verified: Burp Comparer is a manual two-pane tool; Caido has no cross-session diff; no examined tool diffs responses with noise normalization or links results to hypotheses.
- **Workarounds:** Copy-pasting into diff tools; ad-hoc scripts; skipping rigorous multi-account tests.
- **HunterFlow response:** HAR/proxy-export import; sanitized request/response pairs; side-by-side comparison with synchronized scrolling, meaningful diff highlighting, and configurable normalization (headers, dynamic values); explicit rule: status-code differences alone never imply a vulnerability.
- **Feasibility:** Medium — diff/normalization engine is well-bounded; import formats (HAR) are documented standards.
- **Differentiation:** High — verified gap; directly serves the API-security persona.

## PS-5: Findings, evidence, and reports are assembled by hand

- **Problem:** Producing a submission-ready report means manually gathering requests, responses, screenshots, and reproduction steps from proxy histories and note files. Claims are rarely labeled by verification status.
- **Personas:** P1, P2, P3, P6.
- **Current state:** DefectDojo/Ghostwriter produce team-oriented HTML/DOCX reports from imported scanner data; Burp/Caido have no bug-bounty-native reporting; no examined tool generates Markdown/JSON reports directly from linked, verified evidence.
- **Workarounds:** Word templates, screenshot folders, manual markdown.
- **HunterFlow response:** Findings lifecycle (Potential → Under Investigation → Verified → Report Ready → Reported/Resolved/False Positive/Duplicate); evidence linking with integrity + redaction; duplicate detection; Markdown/JSON/HTML report generator with explicit verification labeling.
- **Feasibility:** High — data model + template rendering.
- **Differentiation:** High — verified gap.

## PS-6: "What should I investigate next?" is answered by gut feeling

- **Problem:** With hundreds of discovered endpoints, prioritization is ad-hoc. Nothing explains why an endpoint deserves attention, and priorities are not reusable across sessions.
- **Personas:** P1, P3, P4.
- **Current state:** reconFTW "hotlists" are per-scan; no examined tool provides explainable, cross-session research prioritization.
- **Workarounds:** Mental heuristics (auth pages, IDs in paths), manual lists.
- **HunterFlow response:** Deterministic, rule-based priority scoring with visible factor breakdown (new asset, auth-sensitive, unusual response, untested, recent change, researcher weight). Explicit disclaimer: score ≠ vulnerability. Configurable weights; optional local-AI analysis post-MVP.
- **Feasibility:** High — pure computation over inventory state.
- **Differentiation:** Medium-High — useful but secondary to PS-2/3/4.

## PS-7: No reliable answer to "what changed?"

- **Problem:** Programs evolve; assets appear and disappear; endpoints change. Researchers re-derive this by re-running scans and eyeballing diffs; temporary network failures get mistaken for asset removal.
- **Personas:** P1, P5, P6.
- **Current state:** reconFTW has a file-diff mode; no tool distinguishes transient unavailability from confirmed removal with observation history.
- **Workarounds:** Repeated full scans, manual diffing.
- **HunterFlow response:** Post-MVP continuous monitoring: snapshots, new/removed/changed detection with observation-status semantics (transient vs confirmed), change history, opt-in notifications.
- **Feasibility:** Medium — depends on stable job scheduling + inventory diffing.
- **Differentiation:** Medium — post-MVP milestone.

---

## Evaluation Summary

| ID | Feasibility | Differentiation | MVP? |
|---|---|---|---|
| PS-1 | High | High | Yes |
| PS-2 | Medium-High | High | Yes (core safety) |
| PS-3 | High | Very High | Yes (core identity) |
| PS-4 | Medium | High | Yes |
| PS-5 | High | High | Yes |
| PS-6 | High | Medium-High | Yes (rule-based scoring) |
| PS-7 | Medium | Medium | Post-MVP |

The MVP delivers PS-1 through PS-6; PS-7 lands as the first post-MVP milestone.
