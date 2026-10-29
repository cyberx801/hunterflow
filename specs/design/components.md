# HunterFlow — Component Inventory

- **Version:** 0.1.0 (Draft for G3)
- Legend: [ui] shadcn base · [layout] shell · [domain] module-specific.

## Layout

| Component | Notes |
|---|---|
| AppShell [layout] | sidebar + topbar + content; collapsed sidebar <1024px |
| Sidebar [layout] | nav groups; active rail; settings pinned bottom |
| Topbar [layout] | program picker, ⌘K trigger, job indicator, user menu |
| Breadcrumbs [layout] | program > section > entity |
| PageHeader [layout] | title, scope badge, primary/secondary actions |

## Programs & Scope

| Component | Notes |
|---|---|
| ProgramForm [domain] | RHF+Zod; platform select; notes |
| ProgramList [domain] | table; platform filter |
| ScopeRuleTable [domain] | rule rows w/ effect badge, priority reorder, delete |
| ScopeRuleEditor [domain] | kind-specific fields; live validation |
| ScopePreview [domain] | input → per-target decision cards (matched rules, confirmation flag) |
| PolicyVersionDiff [domain] | v(n-1) → v(n) rule diff |
| ConfirmTargetDialog [domain] | blocking dialog for needs_confirmation (quotes rules; audit-logged) |

## Recon

| Component | Notes |
|---|---|
| ScanForm [domain] | profile select (declarative), target subset, dry-run |
| JobsTable [domain] | status, progress bar, cancel |
| JobDetail [domain] | steps timeline; ToolRunRow (args redacted, exit, logs); failure classification badge |
| JobIndicator [layout] | topbar compact progress |

## Assets & Endpoints

| Component | Notes |
|---|---|
| AssetTable [domain] | TanStack table; type/scope-status badges; tags; bulk tag |
| AssetDetail [domain] | related assets, resolved IPs, tech chips, cards, history |
| EndpointTable [domain] | method badge, path mono, category chips, auth indicators |
| EndpointDetail [domain] | params, body shape, status distribution mini-histogram (real data), research actions |
| CategoryChips [domain] | filter + manual override |

## Research

| Component | Notes |
|---|---|
| CardBoard / CardList [domain] | status columns (board) or table; saved filters |
| CardDetail [domain] | sections: hypothesis, links, methodology, checklist, observations/notes, evidence, history timeline |
| TemplatePicker [domain] | templates + checklists instantiation |
| StatusStateMachine [domain] | transition buttons per current status (validated transitions only) |

## Traffic & Comparison

| Component | Notes |
|---|---|
| TrafficTable [domain] | method/status/host/path/account; redacted badge |
| TransactionDetail [domain] | request/response viewers, truncation + expand |
| RequestViewer / ResponseViewer [domain] | mono, syntax-aware-ish (headers/body), copy |
| DiffViewer [domain] | side-by-side, line diffs, synchronized scroll |
| ComparisonToolbar [domain] | normalization profile select, ignore-header toggles |
| ComparisonNotice [domain] | review-required notice (status-code-only difference) |

## Findings & Reports

| Component | Notes |
|---|---|
| FindingTable [domain] | severity + validation co-badges; status chips |
| FindingWorkspace [domain] | sections incl. reproduction steps, evidence links, duplicate candidates |
| DuplicateCandidates [domain] | match explanation (endpoint/category/similarity) |
| EvidencePicker [domain] | upload w/ limits + link existing |
| ReportEditor [domain] | finding selection, format, preview, export |

## Shared

StatusBadge [domain], ScopeBadge [domain], MonoValue (copy) [domain], EmptyState [layout], ConfirmDialog [ui], FilterPopover [domain], SavedFilters [domain], AuditTable [domain], WeightSliders [domain].
