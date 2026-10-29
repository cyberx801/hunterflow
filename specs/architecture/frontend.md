# HunterFlow — Frontend Architecture

- **Version:** 0.1.0 (Draft for G2) · See `specs/design/*` for visual specs.

## 1. Stack

Next.js (App Router) + TypeScript + Tailwind CSS + shadcn/ui + TanStack Query + TanStack Table + React Hook Form + Zod + Lucide. Server components for data-independent shells; client components for interactive views. No state library beyond Query for server state + local component state.

## 2. Layout

```
web/
├── app/
│   ├── (auth)/login/page.tsx
│   └── (app)/
│       ├── layout.tsx              # shell: sidebar, topbar, program picker
│       ├── overview/page.tsx
│       ├── programs/[id]/(workspace)/…   # program-scoped tabs
│       ├── recon/page.tsx  jobs/[id]/page.tsx
│       ├── assets/page.tsx  [id]/page.tsx
│       ├── endpoints/page.tsx  [id]/page.tsx
│       ├── research/page.tsx  [id]/page.tsx
│       ├── traffic/page.tsx  compare/[setId]/page.tsx  transactions/[id]/page.tsx
│       ├── findings/page.tsx  [id]/page.tsx
│       ├── reports/page.tsx  [id]/page.tsx
│       └── settings/(tabs)
├── components/
│   ├── ui/                 # shadcn primitives
│   ├── layout/             # sidebar, topbar, breadcrumbs, job-indicator
│   └── domain/             # asset-table, endpoint-chip, scope-preview, request-viewer,
│                           #   response-viewer, diff-viewer, status-badge, finding-card…
├── features/               # per-module logic + query hooks + forms
├── lib/api/                # typed fetch client generated from OpenAPI (manual mirror in MVP)
└── lib/format/             # time, bytes, severity, status helpers
```

## 3. Data & State

- **TanStack Query** for all server state; mutation invalidation per entity key; optimistic updates only where trivially safe (checklist toggles).
- **React Hook Form + Zod** for every form; Zod schemas mirror backend `schemas/` (checked by CI test comparing OpenAPI types where practical).
- **Pagination/filter/sort state** serialized to URL search params (shareable/bookmarkable views).
- **Polling:** job progress via short-interval refetch (2s) with backoff when idle; global job indicator in topbar.

## 4. Rendering Rules

- Technical values (domains, paths, tokens, hashes) render in monospace; copy-on-click.
- Large bodies truncated with explicit "expand (n KB)" affordance.
- Diff viewer: line-based with synchronized scroll (see design/components.md).
- All tables: TanStack Table with sticky headers, column toggles, density presets (compact default).

## 5. Security-Sensitive UI Rules

- Scope status shown on every target-affecting action; `needs_confirmation` renders a blocking confirm dialog quoting the matched rules (HF-FR-009).
- Severity/status badges use semantic colors; unverified findings can never render as "Verified".
- No client-side routing to raw evidence; downloads via authenticated API only.
