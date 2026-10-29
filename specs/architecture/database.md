# HunterFlow — Database Architecture (ER Model)

- **Version:** 0.1.0 (Draft for G2) · PostgreSQL 16+ primary; SQLite dev-only convenience (ADR-005).
- Conventions: UUIDv4 PKs, `created_at`/`updated_at` `timestamptz`, soft delete via `archived_at` where noted, JSONB for flexible metadata, every row carries `program_id` where user data (future multi-user path: `user_id` columns added later — zero-cost consideration only, not implemented).

## 1. Entity Groups

### Identity & Policy
- **users** (id, username, password_hash, created_at, is_active)
- **sessions** (id, user_id FK, token_hash, csrf_secret, expires_at, revoked_at)
- **programs** (id, name, platform, url, description, notes_md, policy_source_url, last_policy_review, archived_at, timestamps)
- **scope_rules** (id, program_id FK, policy_version_id FK, kind, value, effect, priority, notes, timestamps)
- **policy_versions** (id, program_id FK, version, change_summary, snapshot JSONB, created_at) — immutable

### Discovery
- **assets** (id, program_id FK, type ENUM(domain, subdomain, ip, url, web_service, api_endpoint), value_normalized UNIQUE(program, type, value), value_original, scope_status ENUM(in_scope, out_of_scope, needs_confirmation), http_status, tech JSONB, tags TEXT[], notes, first_seen, last_seen, timestamps)
- **asset_relations** (id, program_id, parent_id FK, child_id FK, kind ENUM(resolves_to, parent_domain, redirects_to, serves))
- **asset_observations** (id, program_id, tool_run_id FK NULL, import_job_id FK NULL, raw JSONB, normalized_to asset_id FK NULL, observed_at) — immutable source records
- **endpoints** (id, program_id, asset_id FK, method, path, query_params JSONB, content_types JSONB, body_shape JSONB, auth_indicators JSONB, category, status_distribution JSONB, first_seen, last_seen, timestamps; UNIQUE(program, asset, method, path))
- **endpoint_observations** (id, endpoint_id FK, tool_run_id FK, raw JSONB, observed_at)

### Execution
- **tools** (id, name UNIQUE, version, path, available, last_checked)
- **scan_jobs** (id, program_id FK, profile, policy_version_id FK, target_filter JSONB, status ENUM(queued, running, completed, failed, cancelled), cancel_requested BOOL, error_code, progress JSONB, started_at, finished_at, created_by FK users)
- **tool_runs** (id, scan_job_id FK, tool, version, args JSONB, exit_code, timeout_seconds, stdout_ref, stderr_ref, output_ref, started_at, finished_at, status)
- **import_jobs** (id, program_id FK, kind ENUM(har), file_ref, account_tag, status, counts JSONB, error_code, timestamps)

### Research & Traffic
- **http_transactions** (id, program_id FK, source ENUM(har_import, manual), account_tag, method, url, request_headers JSONB, request_body_ref, response_status, response_headers JSONB, response_body_ref, timing JSONB, redacted BOOL, hash UNIQUE, endpoint_id FK NULL, timestamps)
- **comparison_sets** (id, program_id, name, normalization_profile_id FK NULL, timestamps)
- **comparison_members** (set_id FK, transaction_id FK, position)
- **normalization_profiles** (id, name, ignore_headers JSONB, dynamic_rules JSONB, timestamps)
- **research_cards** (id, program_id, asset_id FK NULL, endpoint_id FK NULL, hypothesis, test_category, required_authorization, required_accounts, methodology, status ENUM(not_started, in_progress, needs_verification, confirmed, rejected, blocked, archived), observations_md, notes_md, next_action, timestamps)
- **card_status_history** (id, card_id FK, from, to, at, by)
- **research_templates** (id, program_id NULL, name, body JSONB, timestamps)
- **checklists / checklist_items** (id, card_id FK, label, checked, position)

### Findings & Evidence
- **findings** (id, program_id, title, description, category, cwe, asset_id FK NULL, endpoint_id FK NULL, severity, confidence, impact, reproduction_steps, status ENUM(potential, under_investigation, verified, false_positive, duplicate, report_ready, reported, resolved), validation_status ENUM(unverified, verified_human), discovery_source ENUM(tool_observation, research_card, manual), source_ref, timestamps)
- **finding_status_history** (id, finding_id FK, from, to, at, by)
- **finding_links** (id, finding_id FK, linked_finding_id FK, kind ENUM(duplicate_of, related), note) — provenance preserved; no destructive merge
- **evidence_files** (id, program_id, filename, stored_path, sha256, size, mime, redacted BOOL, retention_days NULL, timestamps)
- **evidence_links** (id, evidence_id FK, finding_id FK NULL, card_id FK NULL, transaction_id FK NULL)
- **reports** (id, finding_id FK NULL (multi via report_findings), format ENUM(markdown, json, html), template_version, content_ref, generated_at)

### Platform
- **audit_events** (id, actor_id FK NULL, action, entity_type, entity_id, before JSONB, after JSONB, correlation_id, ip, created_at) — append-only via API
- **settings** (key UNIQUE, value JSONB, updated_at)
- **saved_filters** (id, program_id NULL, entity_type, name, definition JSONB)

## 2. Key Indexes

- assets(program_id, type, value_normalized) UNIQUE; assets(program_id, last_seen DESC)
- endpoints(program_id, asset_id, method, path) UNIQUE; endpoints(category), (path) text_pattern for LIKE filters
- http_transactions(hash) UNIQUE; (program_id, url_host, method)
- scan_jobs(program_id, status, created_at)
- research_cards(program_id, status)
- findings(program_id, status)
- audit_events(created_at), (entity_type, entity_id)

## 3. Integrity & Provenance Rules

1. Source observations (raw) are immutable and never updated after creation.
2. Normalized entities only created by the normalization service, referencing their observation.
3. `scope_status` on assets is derived from the policy engine, cached on write, recomputed on policy change.
4. Deletes: evidence and audit rows are never hard-deleted by normal flows; assets/endpoints/cards/findings support archive; reports/tool outputs follow retention settings.
5. `policy_versions.snapshot` lets any historical job reproduce the policy it ran under.

## 4. ER Sketch

```
programs 1─* scope_rules ─* policy_versions (immutable)
programs 1─* assets 1─* endpoints 1─* research_cards *─* evidence_files
programs 1─* scan_jobs 1─* tool_runs ─* asset_observations ─ assets
programs 1─* http_transactions *─* comparison_members *─1 comparison_sets
findings *─* evidence_files (via evidence_links); findings 1─* finding_links
findings 1─* reports (via report_findings)
users 1─* sessions; users 1─* audit_events(actor)
```
