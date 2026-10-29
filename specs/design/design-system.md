# HunterFlow — Design System

- **Version:** 0.1.0 (Draft for G3)
- **References:** Linear, Grafana, GitHub, Vercel for interaction patterns; Caido/Burp for technical data density. No copied branding.

## 1. Visual Direction

A serious technical workstation. Deep neutral surfaces, hairline borders, one restrained accent, semantic status colors, monospace for technical values. **Dark mode is the default and the reference design**; light mode is a stretch goal (HF-FR-180).

### Color tokens (dark)

| Token | Value | Use |
|---|---|---|
| `bg-app` | `#0B0E12` | app background |
| `bg-surface` | `#12161C` | cards, panels |
| `bg-raised` | `#1A2027` | hover/raised controls |
| `border` | `#232B34` | hairline borders |
| `border-strong` | `#2E3945` | focus/emphasis borders |
| `text-primary` | `#E6EAF0` | primary text (contrast ≥ 13:1) |
| `text-secondary` | `#9AA6B2` | secondary text (≥ 7:1) |
| `text-muted` | `#66727E` | tertiary (≥ 4.5:1 on bg-app) |
| `accent` | `#F59E0B` (amber) | primary actions, focus, active states |
| `accent-hover` | `#FBBF24` | hover |
| `danger` / `warning` / `success` / `info` | `#F87171` / `#FBBF24` / `#34D399` / `#60A5FA` | semantic statuses |

Light theme derives the same roles (invert surfaces; adjust text contrast to ≥ 4.5:1) — implemented only if time allows after MVP acceptance.

### Typography

- UI sans: **Inter** (400/500/600/700).
- Technical mono: **JetBrains Mono** (400/600) for: domains, hosts, IPs, paths, headers, tokens, hashes, timestamps.
- Scale: 12/13/14/16/20/24/30 px. Body 14; table cells 13; dense captions 12.

### Spacing & layout

- 4px base grid; container padding 24; panel padding 16; gap 8/12.
- Max content width 1440px; tables full-bleed within content area.
- Panel radius 6px; borders 1px hairline; shadows reserved for popovers/menus only (subtle, `0 4px 16px rgba(0,0,0,.35)`).

### Motion

- Transitions ≤ 120ms, transform/opacity only; no decorative animation. `prefers-reduced-motion` disables all non-essential motion.

## 2. Core Primitives (shadcn/ui base, restyled)

Buttons (default/secondary/ghost/destructive; sizes sm/md), inputs with monospace option, selects, checkbox/switch, badge (status colors), tooltip, dialog, dropdown menu, tabs, table (density: compact default, comfortable option), skeleton, toast, popover, command palette (kbd `Ctrl+K`).

## 3. Status Semantics (single source of truth)

| Domain | Values → color |
|---|---|
| Asset scope | in_scope=success · out_of_scope=neutral · needs_confirmation=warning |
| Card status | not_started=muted · in_progress=info · needs_verification=warning · confirmed=success · rejected=danger · blocked=warning · archived=muted |
| Finding status | potential=muted · under_investigation=info · verified=success · false_positive=danger · duplicate=neutral · report_ready=accent · reported=info · resolved=success |
| Validation | unverified=warning · verified_human=success |
| Job status | queued=muted · running=info(pulse) · completed=success · failed=danger · cancelled=neutral |
| Severity | info/low/medium/high/critical mapped to muted/info/warning/danger/danger-strong — severity never rendered before verification state |

Rules: badges always text+icon, never color-only; verified/unverified state is always co-displayed with severity.

## 4. Data Presentation Rules

- Monospace for all technical values; copy-on-click with subtle feedback.
- Diff view: removed=red-tinted row, added=green-tinted row, context=unchanged; line numbers; synchronized scrolling.
- Tables: sticky header, sortable columns, column manager, URL-synced filters, row click → detail; density compact by default.
- Large bodies: preview truncated at 2000 chars with byte count + expand.
- Empty states: one-line explanation + primary action; never decorative heroes.
- Loading: skeletons for lists/tables; inline spinners for buttons; job progress in topbar as compact step indicator.

## 5. Accessibility Baseline (see accessibility.md)

Focus ring 2px accent on all interactive elements; keyboard nav for menus/tables; `aria` labels on icon-only controls; contrast per tokens above; reduced-motion respected.

## 6. Iconography

Lucide, 16px default, stroke 1.75. No emojis in UI.
