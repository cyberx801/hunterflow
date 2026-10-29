# HunterFlow — Accessibility Specification

- **Version:** 0.1.0 (Draft for G3) · Target: WCAG 2.2 AA where practical (HF-NFR-007).

## 1. Keyboard

- All interactive elements reachable via Tab; logical order; no keyboard traps (tested in E2E).
- Global: `⌘K` palette; `?` shows shortcuts help; Escape closes dialogs/popovers.
- Tables: focusable rows, Enter opens detail; column sorting reachable from header buttons.
- Board (research): arrow-key navigation between cards and columns; Space toggles checkboxes.
- Diff viewer: synchronized scroll honors keyboard (PgUp/PgDn panes together).

## 2. Screen Reader

- Landmarks: `nav` (sidebar), `main`, `banner` (topbar), breadcrumb `nav aria-label`.
- Icon-only controls carry `aria-label` or visible tooltip; status conveyed by text badges, never color alone.
- Live regions (`aria-live=polite`) for: job completion, toast errors, import results.
- Dialogs use focus trap + `aria-modal`; focus returns to trigger.

## 3. Contrast & Text

- Text tokens meet ≥ 4.5:1 (secondary) / ≥ 13:1 (primary) on their surfaces (design-system tokens verified in CI via a token-audit script).
- Body 14px default; zoom to 200% must preserve layout (fluid widths, no fixed-height rows with clipped content).

## 4. Forms

- Every input: visible label, error messages linked via `aria-describedby`, required states announced.
- Validation summaries on submit; focus moves to first error.

## 5. Motion

- `prefers-reduced-motion: reduce` disables pulse animations (job indicator), transitions, and auto-scroll.
- No flashing content; loading states non-blinking.

## 6. Verification

- Playwright E2E includes keyboard-only critical path (F3, F4, F6) and an axe-core spot-check on key screens in CI.
