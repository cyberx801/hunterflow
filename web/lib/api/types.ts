export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface Program {
  id: string;
  name: string;
  platform: string;
  url: string | null;
  description: string | null;
  notes_md: string | null;
  policy_source_url: string | null;
  last_policy_review: string | null;
  archived_at: string | null;
  current_policy_version: number;
  created_at: string;
  updated_at: string;
}

export interface ScopeRule {
  id: string;
  kind: string;
  value: string;
  effect: string;
  priority: number;
  notes: string | null;
}

export interface PolicyVersion {
  id: string;
  version: number;
  change_summary: string | null;
  created_at: string;
  rule_count: number;
}

export interface Asset {
  id: string;
  program_id: string;
  type: string;
  value_normalized: string;
  value_original: string;
  scope_status: string;
  http_status: number | null;
  tech: string[] | null;
  tags: string[] | null;
  notes: string | null;
  first_seen: string;
  last_seen: string;
  endpoint_count: number;
  card_count: number;
  priority_score: number;
}

export interface Endpoint {
  id: string;
  program_id: string;
  asset_id: string;
  method: string;
  path: string;
  category: string;
  category_manual: boolean;
  auth_indicators: Record<string, unknown> | null;
  status_distribution: Record<string, number> | null;
  content_types: string[] | null;
  first_seen: string;
  last_seen: string;
  card_count: number;
  priority_score: number;
  asset_value: string | null;
}

export interface ResearchCard {
  id: string;
  program_id: string;
  asset_id: string | null;
  endpoint_id: string | null;
  title: string;
  hypothesis: string | null;
  test_category: string | null;
  required_authorization: string | null;
  required_accounts: string | null;
  methodology: string | null;
  status: string;
  observations_md: string | null;
  notes_md: string | null;
  next_action: string | null;
  priority_score: number;
  priority_factors: Record<string, boolean> | null;
  checklist: { id: string; label: string; checked: boolean; position: number }[];
  created_at: string;
  updated_at: string;
}

export interface ResearchTemplate {
  id: string;
  name: string;
  body: {
    title_pattern?: string;
    hypothesis?: string;
    test_category?: string;
    methodology?: string;
    checklist?: string[];
  };
  created_at: string;
}

export interface Transaction {
  id: string;
  program_id: string;
  source: string;
  account_tag: string | null;
  method: string;
  url: string;
  response_status: number | null;
  redacted: boolean;
  created_at: string;
}

export interface TransactionDetail extends Transaction {
  request_headers: Record<string, string> | null;
  request_body: string | null;
  response_headers: Record<string, string> | null;
  response_body: string | null;
  timing: Record<string, unknown> | null;
}

export interface Comparison {
  id: string;
  name: string;
  created_at: string;
  member_count: number;
}

export interface ComparisonDetail {
  id: string;
  name: string;
  panes: {
    label: string;
    method: string;
    url: string;
    request_headers: Record<string, string>;
    request_body: string | null;
    status: number | null;
    response_headers: Record<string, string>;
    response_body: string | null;
  }[];
  body_diff: { kind: string; left: string | null; right: string | null }[];
  header_diff: Record<string, [string | null, string | null]>;
  status_diff: boolean;
  review_required: boolean;
  review_reason: string | null;
}

export interface Finding {
  id: string;
  program_id: string;
  title: string;
  description: string | null;
  category: string | null;
  cwe: string | null;
  asset_id: string | null;
  endpoint_id: string | null;
  severity: string | null;
  confidence: string | null;
  impact: string | null;
  reproduction_steps: string | null;
  status: string;
  validation_status: string;
  discovery_source: string;
  source_ref: string | null;
  created_at: string;
  updated_at: string;
}

export interface Evidence {
  id: string;
  program_id: string | null;
  filename: string;
  sha256: string;
  size: number;
  mime: string;
  redacted: boolean;
  created_at: string;
}

export interface Report {
  id: string;
  finding_id: string;
  format: string;
  generated_at: string;
  content?: string | null;
}

export interface ScanJob {
  id: string;
  program_id: string;
  profile: string;
  status: string;
  dry_run: boolean;
  error_code: string | null;
  progress: Record<string, unknown> | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}

export interface JobDetail extends ScanJob {
  policy_version: number | null;
  tool_runs: {
    id: string;
    tool: string;
    version: string | null;
    args: string[];
    exit_code: number | null;
    status: string;
    timeout_seconds: number;
    started_at: string;
    finished_at: string | null;
  }[];
}

export interface ScanProfile {
  id: string;
  label: string;
  description: string;
  steps: string[];
  requires_templates: boolean;
}

export interface CuratedTemplate {
  id: string;
  name: string;
  severity: string;
  category: string;
}

export interface Overview {
  program_count: number;
  asset_count: number;
  endpoint_count: number;
  finding_count: number;
  unverified_finding_count: number;
  active_scan_count: number;
  research_queue: { id: string; title: string; status: string; priority_score: number; factors: Record<string, boolean> | null }[];
  findings_needing_verification: { id: string; title: string; severity: string | null; status: string }[];
  recent_changes: { type: string; value: string; at: string }[];
  recent_activity: { action: string; entity_type: string | null; entity_id: string | null; at: string }[];
}

export interface AuditEvent {
  id: string;
  action: string;
  entity_type: string | null;
  entity_id: string | null;
  correlation_id: string | null;
  ip: string | null;
  created_at: string;
}

export interface SettingsView {
  weights: Record<string, number> | null;
  evidence_max_mb: number;
  evidence_retention_days: number;
  tools: { name: string; version: string | null; available: boolean; last_checked: string | null }[];
}

export interface Schedule {
  id: string;
  program_id: string;
  profile: string;
  interval_minutes: number;
  enabled: boolean;
  notify: boolean;
  targets: string[] | null;
  templates: string[] | null;
  next_run_at: string;
  last_run_at: string | null;
  last_job_id: string | null;
  created_at: string;
}

export interface MonitoringEvent {
  id: string;
  program_id: string;
  scan_job_id: string | null;
  kind: string;
  entity_type: string;
  entity_id: string | null;
  entity_value: string;
  detail: Record<string, unknown> | null;
  created_at: string;
}

export interface MonitoringStatus {
  webhook_configured: boolean;
  scheduler_interval_seconds: number;
  min_schedule_minutes: number;
}

export interface AiStatus {
  enabled: boolean;
  model: string;
  endpoint_configured: boolean;
  api_key_configured: boolean;
}

export interface AiSummary {
  text: string;
  model: string;
  source_chars: number;
  disclaimer: string;
}

export interface UserAccount {
  id: string;
  username: string;
  is_admin: boolean;
  is_active: boolean;
  created_at: string;
}

