# HunterFlow — Product Vision

- **Version:** 0.1.0 (Draft, Phase 0)
- **Date:** 2026-10-29
- **Status:** Draft — pending approval gate G1
- **Related:** [personas.md](personas.md), [competitive-analysis.md](competitive-analysis.md), [problem-statements.md](problem-statements.md), [non-goals.md](non-goals.md)

## 1. Name and Tagline

**HunterFlow**

*From Recon to Research. One Intelligent Workspace.*

## 2. Mission

Help authorized security researchers move efficiently from reconnaissance to structured investigation and evidence-backed reporting — while making authorization and scope enforcement a built-in property of every automated step.

HunterFlow is a research assistant and workflow system. It is **not** an autonomous exploitation platform.

## 3. Problem

Bug bounty research today is fragmented across dozens of CLI tools, proxy histories, notebooks, and spreadsheets:

- Recon results live in per-target file trees and terminal scrollback; there is no persistent, queryable inventory across sessions.
- The researcher's own intellectual work — hypotheses, tests, rejections, observations — is scattered across notes and memory.
- Scope and authorization tracking is manual, and program policies change over time.
- Evidence for a finding is assembled by hand, and reports are written from scratch each time.
- There is no reliable answer to "what did I already test?", "what changed?", or "what should I look at next?"

Existing tools each solve a slice: reconFTW and ProjectDiscovery automate discovery; Burp and Caido handle traffic; Faraday and DefectDojo manage findings for teams. None connects **authorization-aware discovery** to **hypothesis-driven research** and **evidence-backed reporting** in a single self-hosted workspace.

## 4. Product Summary

HunterFlow is a self-hosted, open-source workspace that manages the complete bug bounty research lifecycle:

1. Program and scope management with machine-enforced authorization policy
2. Reconnaissance orchestration over proven open-source tools
3. Normalized asset and endpoint inventories with provenance
4. Research cards that connect hypotheses to endpoints, tests, evidence, and findings
5. HTTP traffic import and side-by-side comparison across test sessions
6. Structured findings lifecycle with duplicate detection
7. Evidence management with integrity and redaction
8. Explainable prioritization of research opportunities
9. Professional Markdown/JSON/HTML report generation
10. Continuous monitoring (post-MVP) with change detection

## 5. Differentiation

HunterFlow does not claim that recon, scanning, proxying, or vulnerability management are novel. Its value is the **coherent workflow** between them:

| Pillar | What it means |
|---|---|
| **A. Research-centered workflow** | Recon results connect directly to actionable hypotheses, test cases, evidence, and findings — not a dead-end list of URLs. |
| **B. Authorization-aware automation** | Every active outbound operation passes through a centralized, versioned scope policy. Exclusions, redirects, and ambiguous targets are handled by policy, not memory. |
| **C. Research continuity** | What was discovered, tested, verified, rejected, and planned is preserved across sessions, tools, and devices. |
| **D. Evidence-driven findings** | Every finding traces back to an asset, endpoint, test case, observation, and sanitized evidence. Claims are labeled by verification status. |
| **E. Explainable prioritization** | "What next?" is answered by transparent, deterministic signals — never unsubstantiated vulnerability claims. |
| **F. Open-source and self-hosted** | Fully functional locally with Docker Compose; no mandatory cloud services, subscriptions, or commercial APIs. |

## 6. Target Users

- **Primary:** independent bug bounty hunters; web application penetration testers; API security researchers.
- **Secondary:** security students; security engineers; authorized red-team practitioners; small security research teams.

## 7. Success Criteria (v0.1.0)

1. A researcher can install HunterFlow locally with one Docker Compose command.
2. The complete workflow — program → scope → recon → assets/endpoints → hypothesis → traffic comparison → finding → evidence → report — works end to end in the MVP.
3. No active network operation can run against an out-of-scope target, including through redirects.
4. A researcher can reproduce any finding from its stored evidence.
5. The platform never claims an unverified observation is a confirmed vulnerability.
6. The core path is covered by automated tests, including security tests.
7. A new contributor can start developing from `README.md` in under 30 minutes.

## 8. Release Scope

v0.1.0 is the "Research Workspace MVP" defined in `specs/product-requirements.md` (Phase 2). Deferred features are listed in [non-goals.md](non-goals.md) and the product requirements document.
