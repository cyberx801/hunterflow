# HunterFlow — Competitive Analysis

- **Version:** 0.1.0 (Draft, Phase 0)
- **Date:** 2026-10-29
- **Research method:** Public READMEs, official docs, and repository metadata fetched 2026-10-29 (GitHub + project sites). No proprietary feature claims assumed; where a feature could not be verified, it is marked unverified.
- **Sources:** github.com/six2dez/reconftw, github.com/projectdiscovery/* (subfinder, httpx, katana, nuclei, dnsx, notify, nuclei-templates), github.com/owasp-amass/amass, github.com/infobyte/faraday, github.com/DefectDojo/django-DefectDojo, caido.io, portswigger.net/burp, github.com/GhostManager/Ghostwriter, github.com/cisagov/redeye.

## 1. Landscape

| Tool | Category | License | Output model | Fits HunterFlow as |
|---|---|---|---|---|
| **subfinder** | Passive subdomain discovery | MIT | JSONL / stdout | Managed tool (recon) |
| **httpx** | HTTP probing/fingerprinting | MIT | JSONL (can embed raw req/resp) | Managed tool (recon) |
| **katana** | Crawler / endpoint extraction | MIT | JSONL (incl. req/resp, tech, page-type) | Managed tool (recon) |
| **nuclei** | Template-based vulnerability scanner | MIT (engine); MIT (templates) | JSONL, markdown/SARIF/PDF exports | Managed tool (checks, curated templates) |
| **dnsx** | DNS resolution toolkit | MIT | JSONL | Managed tool (recon) |
| **reconFTW** | Bash orchestration of 100+ tools | MIT | Per-target file tree, optional report | Inspiration; not embedded (file-oriented) |
| **OWASP Amass** | Attack-surface mapping | Apache-2.0 | Own graph DB (SQLite), weak JSON | Optional future source; not MVP |
| **Faraday** | Multi-user vuln management + scanner aggregation | GPL-3.0 | Server + web UI (5985), REST API | Not embedded (copyleft; team-oriented) |
| **DefectDojo** | ASPM / vuln management for dev teams | BSD-3-Clause (community) | Web app + REST v2, 200+ parsers | Reference for finding lifecycle; not embedded |
| **Caido** | Web audit proxy | Proprietary (closed, freemium) | Desktop app, project files | Interop via HAR import |
| **Burp Suite** | Web pentest toolkit (industry standard) | Proprietary | Desktop, proprietary project files | Interop via HAR/export; not integrated |
| **Ghostwriter** | Red-team ops + reporting | BSD-3-Clause | Django web app, templated DOCX/XLSX reports | Reference for report templating |
| **Redeye** | C2 log visualization | BSD-3-Clause | Desktop | Out of scope (maintenance mode) |

## 2. What Existing Tools Already Solve (and do well)

- **Discovery breadth:** ProjectDiscovery tools + reconFTW cover passive/active subdomain discovery, probing, crawling, and template scanning comprehensively. HunterFlow will not reimplement these.
- **Traffic manipulation:** Burp and Caido own proxy interception, replay, and manual request editing. HunterFlow will not build a full proxy.
- **Team vulnerability management:** DefectDojo and Faraday normalize scanner reports into team workflows with dashboards and access control.
- **Ops reporting:** Ghostwriter produces formal DOCX/PPTX deliverables for red-team engagements.

## 3. Verified Gaps (HunterFlow's Opportunity)

Research verified the following gaps across **all** examined tools:

1. **No persistent, normalized asset/endpoint inventory across campaigns** — recon tools are stateless per-run; reconFTW writes per-target file trees; nothing gives a cross-program, queryable, deduplicated inventory with history.
2. **No program-level scope/authorization enforcement during active testing** — katana has per-run scope regexes; nuclei has host exclusion flags; but no tool maintains a versioned, program-level policy that gates every outbound operation, including redirects and discovered third parties.
3. **No hypothesis → test → observation → evidence → finding traceability** — Burp/Caido are session-bound; Faraday/DefectDojo start from scanner findings; nothing tracks the researcher's own intellectual work (hypotheses, rejections, multi-account tests).
4. **No systematic HTTP request/response comparison across sessions/accounts** — Burp Comparer is manual and two-way; no tool diffs responses between authorized test accounts with noise normalization.
5. **No duplicate detection across tools and scans for bug-bounty-style findings** — DefectDojo has dedup but only for imported scanner reports; nothing dedups manually-created findings from proxy/hypothesis work.
6. **No bug-bounty-native report generation from research workspace data** — DefectDojo/Ghostwriter are team-oriented (HTML/DOCX); nothing generates Markdown/JSON reports directly from linked evidence and reproduction steps.
7. **No explainable research prioritization** — reconFTW "hotlists" are scan-specific; no tool explains *why* an endpoint deserves attention using researcher-visible signals.

## 4. Interoperability Notes

- **ProjectDiscovery tools** are the cleanest subprocess citizens: MIT-licensed Go binaries, flag-only argument interfaces (no shell string concatenation needed), first-class JSONL output. This makes them ideal managed tools for HunterFlow's recon engine.
- **nuclei-templates** is MIT-licensed; bundling a curated subset with attribution is license-compatible.
- **reconFTW** (MIT) is file-oriented and shell-glue based; HunterFlow will orchestrate its underlying tools directly rather than wrap the bash script.
- **Faraday (GPL-3.0)** must not be embedded; interop would be limited to importing/exporting data at arm's length. Not planned for MVP.
- **Burp** and **Caido** project files are proprietary; HunterFlow interop is via standard HAR import and proxy export formats, not file parsing.
- **HackerOne and Bugcrowd** expose authenticated APIs only (no anonymous free scope feed). Scope ingestion in MVP will be manual/paste-based; authenticated platform sync is a post-MVP, opt-in feature.

## 5. Positioning Statement

HunterFlow does not compete with discovery tools, proxies, or team vulnerability managers. It sits **between** them: a researcher's persistent, authorization-aware workspace that turns tool output into structured research — and structured research into verified, evidence-backed reports. The differentiators are the workflow (research cards, comparison, findings, evidence), the policy layer (scope enforcement), and the ownership model (self-hosted, open source, no paid dependencies).
