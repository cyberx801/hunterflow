# HunterFlow — Screen Specifications

- **Version:** 0.1.0 (Draft for G3)
- Each screen: purpose, regions (top→bottom), key states. Numbers reference components.md.

## S1 — Login / First-run

- Centered card on bg-app; logo wordmark + tagline.
- **Login state:** username, password, submit; rate-limit error display.
- **First-run state:** account creation (username, password + confirm, ≥12 chars policy hint) — shown only when no user exists.
- Footer: version + "self-hosted, local data" note (privacy assurance).

## S2 — Overview

- Purpose: session continuity (F8). Header: "Overview" + program picker (All default).
- Regions:
  1. **Programs strip:** program cards (name, platform, asset/endpoint counts, last activity) + "New program".
  2. **Active scans:** running/queued jobs with progress + link to Recon.
  3. **Research queue:** cards in `in_progress`/`needs_verification` sorted by priority score with factor chips.
  4. **Findings needing verification:** unverified findings count + top rows.
  5. **Recent changes:** since-last-visit feed (new assets/endpoints/findings) with timestamps.
  6. **Activity:** recent audit rows (compact).
- States: fully empty → guided empty state (create program); partial data → sections with empty rows omitted but headers retained; loading → skeletons.

## S3 — Programs list / Program workspace

- List: table (name, platform badge, counts, last review date, status) + search/filter.
- Workspace tabs: **Scope** (S4), Assets, Endpoints, Research, Scans, Findings, Settings (program-level: archive, policy review date, notes).
- Header: program name, platform, policy version chip, "in review since" warning if stale.

## S4 — Scope tab (program)

- Regions: rule table (S3 components) → scope preview panel → policy version history w/ diff.
- Actions: add rule, reorder priorities, save (creates version), test targets.
- Key state: unsaved changes badge; confirmation dialog on save ("This creates policy version vN").

## S5 — Recon

- Left: scan configuration (profile cards with step previews, dry-run toggle, target subset multi-input validated live).
- Right/below: jobs table (status, progress, program, created, duration, cancel).
- Job detail (route): timeline of steps → tool runs → args (redacted, mono) → exit/log → outputs → "results added" summary linking to Assets.

## S6 — Assets

- Toolbar: search, type filter, scope-status chips, tag filter, source filter, saved filters, density toggle, bulk tag.
- Table: value (mono), type, scope badge, http status, tech chips, first/last seen, source, tags.
- Detail: header (value + copy, scope badge, actions), related assets section, endpoints table, research cards, observation history (provenance).

## S7 — Endpoint Explorer

- Toolbar: search (path), method chips, category chips, auth-indicator filter, program picker.
- Table: method badge (GET green-ish neutral, POST accent…), path mono, categories, params count, status distribution sparkline, last seen.
- Detail: parameters table (name, example value, count), body shape preview, auth indicators, status distribution histogram, linked cards, actions (research card, compare, finding).

## S8 — Research Workspace

- View toggle: board (columns = statuses) / table (priority sort).
- Card detail: left = content sections (hypothesis, methodology, accounts, observations, notes, next action); right rail = links (asset, endpoint, comparison set, evidence), status control (valid transitions only), history timeline.
- Template picker modal on create.

## S9 — HTTP Traffic

- Import panel: HAR upload w/ account tag, import progress, last import summary.
- Table: method, status, host, path, account tag, redacted badge, source, time.
- Transaction detail: request/response viewers with truncation.
- Compare view (route): member selector, DiffViewer two/three panes, ComparisonToolbar, ComparisonNotice, save set → link modal (card/finding).

## S10 — Findings

- Table: title, severity badge + validation badge, status, category/CWE, asset, updated; filters + saved filters.
- Workspace: header (title, status, validation control), sections: description, classification (CWE select), affected asset/endpoint, severity/confidence/impact, reproduction steps (markdown), evidence (EvidencePicker), duplicate candidates (DuplicateCandidates), linked cards/transactions, history, "Generate report" action.

## S11 — Reports

- List of generated reports (finding, format, date, download).
- Editor: select finding(s) → format → generate → preview panel (markdown rendered / JSON / HTML iframe-sandboxed) → export.
- Banner: verification status of included findings.

## S12 — Settings

Tabs: **Tools** (detect/refresh, per-tool version/path, nuclei template subset note) · **Auth** (change password, sessions list + revoke) · **Storage** (evidence dir display, size caps, retention, redaction patterns editor) · **Prioritization** (WeightSliders + reset) · **Audit** (AuditTable) · **About** (version, license).
