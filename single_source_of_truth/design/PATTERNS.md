# Interaction Patterns — User Flows

**Owner:** IKB Designer (minimalist environment designer)  
**Last Updated:** 2025-11-09  
**Status:** 🟡 In Progress — Diagnostics-aware search patterns documented

---

## Purpose

This document defines the interaction patterns and user flows for Local Latent Containers UI, including:
- Page-level navigation patterns
- Micro-interactions (hover, focus, active)
- State transitions
- Error and empty states
- Loading patterns

---

### Primary Navigation

**Pattern:** Top navigation bar with horizontal layout

**Anatomy:** Left (logo/app name), center (search bar when on search page), right (diagnostics toggle, container selector)

**States:**
- **Default:** Transparent background, subtle ink text
- **Active (current page):** Ink text with ikb-2 underline indicator
- **Hover:** Background paper-0, border line-2
- **Focus (keyboard):** 1px ink focus ring, visible outline

**Layout:**
- Height: 64px
- Padding: 0 2.5rem
- Item spacing: 2rem
- Logo: 1.5rem font size, weight-light

**Motion:**
- Hover background: 120ms ease-out
- Active indicator: 200ms ease-out
- Focus ring: 120ms ease-out

**Keyboard Navigation:**
- Tab order: Logo → Navigation items → Search → Right actions
- Enter activates links
- Space activates buttons
- Skip link to main content (first tab stop)

**A11y:**
- role="navigation" on container
- aria-label="Main navigation"
- aria-current="page" on active item
- All interactive elements min 40x40px

---

## Search Patterns

### Search Entry
**Flow:**
1. Focus: border transitions line-1 → line-2; diagnostics pill reveals current search mode (Hybrid/Semantic/BM25).
2. User types query; inline helper text reminds of ⌘K focus + Ctrl/⌘+D diagnostics toggle.
3. Submit: Enter or search icon; 100 ms reflection pause locks the button, swaps cursor to busy state.
4. Loading: skeleton list appears, diagnostics rail header switches to "collecting metrics" with animated ellipsis.
5. Results fade in (320 ms ease-in-out) with refreshed diagnostics payload + latency budget badge.

**Empty State:**
- Placeholder: "Search expressionist-art..."; subline "press ⌘K to focus".
- Secondary CTA: "Toggle diagnostics" ghost pill when there is recorded telemetry.
- No autocomplete (Phase 2 backlog), no AI suggestions.

**Error States:**
- No hits: "No results for 'query'. Try broader terms or view diagnostics." Provide inline link to open diagnostics rail.
- Timeout: "Search exceeded local budget. Showing partial results." Append `LATENCY_BUDGET_EXCEEDED` badge next to diagnostics pill.
- Service unavailable: "Search unavailable. Check health status." Offer "View health" action that jumps to diagnostics rail.

---

### Results Display
**Layout:** Vertical list, newest/most-relevant first

**Item Structure:**
- Title (ink-1, 1.25rem, weight-normal)
- Snippet (ink-2, 1rem, clamp 280–320 chars)
- Provenance (ink-2, 0.7rem, uppercase, tracking-wider)
- Score (ikb-2, subtle, right-aligned)

**Interaction:**
- Hover: Border line-1 → line-2, 2px lift (120ms)
- Click: Opens detail modal
- Keyboard: Arrow keys navigate, Enter opens

**Diagnostics Toggle:**
- Inline pill inside search bar; label matches `diagnostics.mode`.
- Keyboard shortcut Ctrl/⌘+D mirrors button state.
- Hover/focus use ghost styles; warning border appears when backend issues present.
- Toggling opens/closes the diagnostics rail (see below) and updates aria-pressed.

### Diagnostics Rail
**Intent:** Show stage timings, latency budgets, hit counts, and SQL health data without overwhelming results.

**Structure:**
1. **Mode & Budget:** Top pill showing current mode + `latency_budget_ms`. If `latency_over_budget_ms > 0`, display secondary badge "+X ms" in `--diag-latency-warn`.
2. **Latency Table:** Rows for `total_ms`, `bm25_ms`, `vector_ms`. Use micro typography; highlight offending row when value > budget.
3. **Hit Chips:** `bm25_hits` and `vector_hits` pills using `--diag-hits-pill-*` tokens.
4. **SQL Health:** When `.artifacts/golden_queries_summary.json` is available, list `chunk_count` and `embedding_cache_rows_total` for the active container—green check when >0, ember warning when 0.
5. **Issues Stack:** Render backend `issues[]` (e.g., `LATENCY_BUDGET_EXCEEDED`) as monochrome list with links to runbook entries.

**Behavior:**
- Auto-opens after any search where latency exceeded budget or hits == 0.
- Collapses with 200 ms width animation; respects reduced-motion (instant toggle).
- Data updates atomically; old values fade to 60% opacity until new payload arrives.

---

## Container Gallery Patterns

### Grid vs List
**Decision Tree:**
- ≤12 containers: 2-column grid, 2.5rem padding, 3–4rem gaps
- >12 containers: Vertical list with group headers by theme

**Card Interaction:**
- Hover: Border darken + 2px lift (120ms)
- Click: Navigate to container search view
- Keyboard: Tab navigation, Enter activates
- Focus: 1px ink focus ring

---

## Modal Patterns

### Document Detail Modal
**Open:**
- Trigger: Click search result
- Animation: 280ms cubic-bezier(.34, 1.56, .64, 1) (slight spring)
- Backdrop: 95% white overlay + subtle blur

**Layout:**
- Left: Image/PDF preview
- Right: Metadata + actions
- Close button: Top-right, ghost variant

**Close:**
- Triggers: X button, Escape key, click backdrop
- Animation: 280ms ease-in-out (symmetrical fade)

**Accessibility:**
- Focus trap within modal
- First focusable element gets focus on open
- Escape key always closes
- Click-away closes (unless form has unsaved changes)

---

## Loading States

### Skeleton Screens
**Usage:** Initial page load, search in progress

**Pattern:**
- Hairline borders (line-1)
- No pulsing animation (prefers-reduced-motion by default)
- Maintain layout (no content shift)
- Diagnostics rail shows placeholder rows (three lines) with shimmering hairline to reinforce active metrics collection.

**Duration:** Show after 200ms delay (avoid flash for fast responses)

---

### Inline Loaders
**Usage:** Button actions (e.g., "Add Document")

**Pattern:**
- Button becomes disabled
- Text replaced with spinner (12px, ink-1)
- Spinner rotates 360° in 800ms (linear)

---

## Empty States

### No Containers
**Message:** "No containers yet. Create your first themed collection."  
**Action:** Primary button "Create Container"  
**Illustration:** Optional (minimal, monochrome)

### No Search Results
**Message:** "No results for 'query'"  
**Suggestions:**
- "Try broader terms"
- "Check spelling"
- "View diagnostics for more detail"

**Action:** Secondary button "Clear Search"

---

## Error States

### Transient Errors (Retry-able)
**Pattern:**
- Banner at top (ember border-left, ink text)
- Message: "Search timeout. Showing partial results."
- Action: "Retry" button (secondary)
- Auto-dismiss after 10s (with undo)
- Diagnostics rail auto-expands with highlighted latency row and inline "View timings" link from banner.

### Permanent Errors (Non-retry-able)
**Pattern:**
- Full-page error (service unavailable)
- Message: "Service unavailable. Check health status."
- Action: "Refresh Page" button (primary)
- No auto-dismiss

---

## Focus Management

### Keyboard Navigation
**Order:**
1. Skip to content link (hidden until focus)
2. Primary nav
3. Search input
4. Results (arrow keys within list)
5. Footer links

**Focus Indicators:**
- 1px ink ring (no glow)
- Border shift (line-1 → line-2)
- Respect prefers-reduced-motion (instant, no transition)

---

## Reduced Motion Variants

**When `prefers-reduced-motion: reduce`:**
- All transitions → instant (0ms)
- Reflection pauses → remain (100ms, for UX clarity)
- Skeleton screens → no pulse
- Modals → instant opacity (no spring)
- Diagnostics rail collapses/expands instantly; latency warnings rely on color/type only (no shake/flash).

---

## Golden Query Review Pattern

**Purpose:** Provide a repeatable UI for reviewing `.artifacts/golden_queries_summary.json` after CI so designers understand regressions without leaving the app.

**Flow:**
1. Diagnostics rail displays "Golden summary" link when artifact detected.
2. Link opens right-side drawer containing:
   - Table of queries (ID, returned, total hits, average timings).
   - SQL check panel summarizing `chunk_count` + `embedding_cache_rows_total` per container.
   - Download button for raw JSON.
3. Drawer closes via ESC, close button, or clicking backdrop.

**States:**
- **Healthy:** All queries returned >0 and chunk_count >0 → rows show check icon, subtle ink background.
- **Regression:** Rows with 0 hits or chunk_count 0 turn ember, include CTA "Inspect ingestion" linking to runbook.

**Accessibility:** Drawer uses focus trap; tables are keyboard navigable; summary metrics announced via aria-live when artifact loads.

---

**Status:** 🟡 In Progress (search + diagnostics patterns defined)  
**Next Action:** Document primary navigation + container gallery micro-interactions  
**Cross-Reference:** COMPONENTS.md, TOKENS.md, ACCESSIBILITY.md
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            