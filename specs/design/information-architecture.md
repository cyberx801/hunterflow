# HunterFlow — Information Architecture

- **Version:** 0.1.0 (Draft for G3)

## 1. Global Shell

```
┌────────────────────────────────────────────────────────────┐
│ Sidebar (240px)            │ Topbar (56px)                 │
│  Overview                  │ [Program picker] [Search ⌘K]  │
│  Programs                  │ [job status] [notifications]  │
│  Recon                     │ [user menu]                   │
│  Assets                    ├───────────────────────────────┤
│  Endpoints                 │ Breadcrumbs / page header     │
│  Research                  │ (title, scope badge, actions) │
│  HTTP Traffic              ├───────────────────────────────┤
│  Findings                  │ Content                      │
│  Reports                   │                               │
│  Settings                  │                               │
└────────────────────────────┴───────────────────────────────┘
```

- **Sidebar:** icon+label, active state accent left-rail; collapsed to icons at <1024px; Settings at bottom group.
- **Topbar:** current program picker (global context, also breadcrumbs on program pages); `⌘K` search across programs/assets/endpoints/findings; live job indicator (spinner + step); user menu.
- **Program context:** choosing a program in the topbar scopes list pages (Assets/Endpoints/Research/Traffic/Findings) to that program; "All programs" remains available.

## 2. Navigation Map

| Route | Purpose | Key child routes |
|---|---|---|
| `/overview` | cross-program summary | — |
| `/programs` | list | `/programs/[id]` workspace with tabs: Scope · Assets · Endpoints · Research · Scans · Findings · Settings |
| `/recon` | scans + jobs | `/recon/jobs/[id]` (steps, tool runs, logs) |
| `/assets` | inventory | `/assets/[id]` (related, endpoints, cards, history) |
| `/endpoints` | endpoint explorer | `/endpoints/[id]` (methods, params, auth, cards, compare) |
| `/research` | cards board/list | `/research/[id]` (card detail, checklist, evidence, history) |
| `/traffic` | imported transactions | `/traffic/transactions/[id]` · `/traffic/compare/[setId]` |
| `/findings` | finding lifecycle | `/findings/[id]` (investigation workspace) |
| `/reports` | report editor | `/reports/[id]` (preview, export) |
| `/settings` | tools · auth · storage · audit · preferences | tabs |

## 3. Cross-References (contextual actions)

- Asset detail → "Open research card", "View endpoints", "Compare traffic", "Record finding".
- Endpoint detail → "Create research card (template)", "Add to comparison", "Findings".
- Research card → linked evidence, comparisons, promotion to finding.
- Finding → linked cards/evidence/transactions, duplicate candidates, "Generate report".
- Every list row exposes kebab menu with module-appropriate actions (max 2 clicks to any primary action).

## 4. Filtering & Search Model

- Lists: quick filter chips (status/type/category) + advanced filter popover; state in URL.
- Global `⌘K`: fuzzy across entities, jump-to-detail.
- Saved filters per entity (HF-FR-063).
