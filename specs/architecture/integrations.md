# HunterFlow — Integrations Architecture

- **Version:** 0.1.0 (Draft for G2) · MVP adapter set + import formats.

## 1. Managed Tools (subprocess adapters)

| Tool | Version pinned | Used for | Key flags | Scope controls available | Residual risk |
|---|---|---|---|---|---|
| **subfinder** | release pin | passive subdomain discovery | `-d`, `-silent`, `-json` (`-oJ`), `-all` off by default | passive; no target requests | none for target; third-party API sources optional |
| **httpx** | release pin | probing/fingerprinting | `-json`, `-silent`, `-follow-redirects` **off**, `-title`, `-tech-detect`, `-status-code`, `-no-color`, rate flags | IP/allow-deny lists; no-follow | redirects not followed (verified flag exists) |
| **katana** | release pin | endpoint extraction | `-jsonl`, `-silent`, `-field-scope` per-run, `-cs`/`-cos` regexes from policy | in/out-scope regexes derived from policy | crawl can reach third-party pages → out-of-scope regexes + post-filter by policy engine |
| **nuclei** | release pin + template subset hash | curated vuln checks | `-jsonl`, `-t` explicit template list, `-follow-redirects` off, `-no-interactsh` default, rate flags | host exclusions; explicit template selection | template bodies control requests; subset curated + reviewed; interactsh off by default |

Rules:
- Args always arrays; never `shell=True`; targets validated by the policy engine first.
- `build_args` output persisted redacted in `tool_runs`.
- Adapter versions recorded via `--version`; availability surfaced in Settings (HF-FR-021).
- Nuclei template subset: shipped in-repo under `integrations/nuclei-templates-curated/` with `templates.lock` (path + sha256 + license note, MIT); new templates require review + owner approval (Constitution P4).

## 2. Import Formats

- **HAR (1.2)** — primary traffic format (HF-FR-070): streamed parse, size-capped entries (e.g., 20 MB/entry), bodies base64-decoded, redaction applied, `account_tag` optional on import.
- **Burp/Caido interop** — via their HAR export; documented walkthrough; proprietary formats explicitly not parsed (HF-FR-071).
- **Raw request/response fixtures** (sanitized) — MVP `manual` transactions typed into UI (method, headers, body) for comparison pairs.

## 3. Adapter → Observation Normalization

Each parser maps tool JSONL to typed `Observation(kind, payload, source_tool_run)`:
- subfinder → `Observation(kind=subdomain, host=…)`
- httpx → `Observation(kind=web_probe, url, status, tech, title, ip)`
- katana → `Observation(kind=endpoint, url, method, params, body_shape, auth_indicators, category_hints)`
- nuclei → `Observation(kind=scanner_finding, template_id, severity, matched_at, request/response refs)`
Normalization service creates/updates assets+endpoints with dedup keys; scanner findings create **potential** findings only (never verified).

## 4. Reuse & Licensing

All four tools MIT; nuclei-templates MIT (curated copy with attribution). No GPL components linked (Faraday/Amass excluded). Versions and licenses recorded in `integrations/tools.lock`.
