# HunterFlow — User Flows

- **Version:** 0.1.0 (Draft for G3)

## F1 — First Run & Onboarding

1. `docker compose up -d` → open http://localhost:3000 → no user exists → **Create account** form (username, password ≥12, confirm).
2. → Overview with empty-state cards: "Create your first program" primary CTA.
3. → Program creation dialog (name, platform, URL, notes) → lands on Scope tab with scope-rule empty state and inline docs hint.

## F2 — Program & Scope Setup

1. Programs → New → fill fields → Save → workspace opens on Scope.
2. Add rules: exact domain, wildcard (`*.example.com`), CIDR, exclusions, method restrictions, automation permissions; each row shows effect badge.
3. **Scope preview panel:** paste candidate targets (`a.example.com`, `evil.net`, `1.2.3.4`) → per-target decision with matched rules + confirmation flag.
4. Save → policy version v1 created; audit event recorded. Editing later creates v2 with diff view.

## F3 — Recon Run

1. Recon → New scan: program, profile (passive/light/web/vuln_checks), optional target subset (validated against policy), dry-run toggle.
2. Pre-flight shows effective policy version + "will test N targets".
3. Submit → job queued → topbar indicator + jobs list shows steps progress.
4. Job detail: per-tool runs, args (redacted), exit codes, logs; cancel anytime.
5. Complete → "New assets: N" summary → links into Assets.

## F4 — Hypothesis Research (core loop)

1. Endpoint `GET /api/orders/{id}` (from katana) → "Create research card".
2. Card auto-filled: asset/endpoint links, suggested category (object-access); pick template "BOLA – object-level authorization".
3. Fill hypothesis, required accounts, methodology; status In Progress; checklist items.
4. Test externally (Burp/Caido) → export HAR → import with account tag.
5. On card: attach comparison set + observations + verdict; status → Needs Verification or Rejected; history preserved.

## F5 — Account Comparison

1. HTTP Traffic → Import HAR (two imports tagged `acct-a`, `acct-b`) → select 2 transactions → "Compare".
2. Comparison view: synchronized diff; normalization profile "default" (ignore Date/Set-Cookie; mask UUIDs/timestamps).
3. Meaningful difference → save comparison set → link to research card.
4. Status-code-only differences render a notice: "Review required — status differences alone do not indicate a vulnerability" (HF-FR-075).

## F6 — Finding & Evidence

1. From card (or scanner observation): "Promote to finding" → finding workspace prefilled.
2. Set severity/confidence/impact; status Under Investigation; attach evidence (upload or link comparison/HAR entry).
3. Human verification checkbox → validation_status verified_human → status Verified (never automatic).
4. Duplicate check: "Find duplicates" → deterministic candidates with similarity explanation → link, provenance preserved.

## F7 — Report

1. Findings → Report Ready (or verified) → "Generate report" → format Markdown/JSON/HTML.
2. Preview with verification banner; sections per spec; export/download.
3. No submit button (N4). Audit event on generation.

## F8 — Session Continuity

1. Login → Overview shows: programs, counts, recent changes (new assets/endpoints since last visit), active scans, cards needing action, findings needing verification, recent activity feed.

## F9 — Settings

Tools tab (detect/versions), Auth (change password/sessions), Storage (evidence dir, size caps, retention), Import (redaction patterns), Prioritization (weights + reset), Audit log tab.
