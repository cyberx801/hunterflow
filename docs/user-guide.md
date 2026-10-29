# User Guide

HunterFlow follows a research loop: **scope → discover → investigate → verify → report**.

## 1. Set up a program

**Programs → New program.** Fill name and platform, then open the program's **Scope** tab and add rules:

| Kind | Example | Meaning |
|---|---|---|
| Wildcard domain | `*.example.com` | authorizes subdomains (NOT the apex) |
| Exact domain | `example.com` | authorizes only that host |
| IP/CIDR | `10.0.0.0/24` | authorizes that network (host must resolve) |
| URL path (deny) | `/admin` | restricts a subpath |
| Method (deny) | `POST` | restricts a method |
| Automation | `confirm` | requires explicit confirmation before automated testing |

**Deny rules always win.** Anything not covered by an explicit allow rule is *blocked* and requires confirmation — HunterFlow never assumes `*.example.com` authorizes third-party services.

Use **scope preview** to test candidate targets, then **publish a policy version** to snapshot the rules (every scan records the policy version it ran under).

## 2. Discover

**Recon → New scan.** Choose a profile:

- **Passive Discovery** — subdomain enumeration (`subfinder`), no requests to discovered hosts.
- **Light Recon** — adds DNS resolution (`dnsx`) and HTTP probing (`httpx`).
- **Web Inventory** — adds passive URL discovery (`gau`) and authorized crawling (`katana`).
- **Passive URL Discovery** — subdomain enumeration plus historical URLs from public sources; no requests to targets.
- **Screenshots** — captures pages of in-scope URLs. Requires an image built with `WITH_SCREENSHOTS=1`; images appear on the asset page.
- **Vulnerability Checks** — curated `nuclei` templates only, explicitly selected.

Optionally restrict targets (must be in scope) or run a **dry run**. Watch progress in the top bar; open the job for per-tool arguments and output (secrets redacted).

## 3. Investigate

**Endpoints →** pick a discovered endpoint. The category and auth indicators are *informational* — they never mean "vulnerable". Click **Research card**, choose a template (e.g. "BOLA / IDOR"), and record your hypothesis, methodology, and checklist.

Work the card through its status: *not started → in progress → needs verification → confirmed / rejected*. Record observations and next actions as you go. Everything is preserved for your next session.

## 4. Compare authorized accounts

**HTTP Traffic → Import HAR** (export from Burp Suite / Caido), optionally tagged with an account name. Headers are redacted on import. Select two transactions and **Compare**: dynamic values (timestamps, UUIDs, tokens) are masked, and header differences are listed.

A status-code-only difference shows a **"Review required"** notice — HunterFlow will never infer a vulnerability from a status code alone.

## 5. Record findings

**Findings → New finding** (or promote a confirmed research card). Findings start as *potential / unverified*. Marking a finding **verified** requires explicit human confirmation (the API refuses otherwise). Use **Find duplicates** to link related findings without destroying provenance.

Attach **evidence** (sanitized requests, responses, screenshots) — files are stored with SHA-256 integrity checks and are only reachable through the authenticated download endpoint.

## 6. Report

**Findings → [finding] → Report → markdown/json/html/pdf.** Reports always carry the verification banner — unverified findings are labeled as such. PDFs and other formats download through an authenticated endpoint. Nothing is ever submitted to a bug bounty platform automatically.

## 7. Prioritization

The research board and endpoints are ranked by a **deterministic, explainable score** (new asset, auth-sensitive, untested, scanner observation, …). Each card shows which factors contributed. A high score is a lead, not a claim — and you can tune the weights in **Settings → Prioritization**.

## 8. Team (optional)

The first account is the administrator. Admins can create members, promote or demote them, disable accounts and reset passwords in **Settings → Users**. Everyone shares the same programs and data; there is no per-user isolation yet. To let people self-register, set `HF_ALLOW_REGISTRATION=true`.

## 9. AI assist (optional, off by default)

If `HF_AI_ENABLED=true` and an OpenAI-compatible endpoint is reachable (local Ollama by default), research cards and findings show an **AI assist** panel. It summarizes only the data on that page, cannot scan or verify anything, and its output is labeled advisory. It is never used for authorization decisions or to mark findings verified.

