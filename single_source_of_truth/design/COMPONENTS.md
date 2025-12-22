# Component Library — Contracts & Specifications

**Owner:** IKB Designer (minimalist environment designer)  
**Last Updated:** ⚪ Not Started  
**Status:** 📝 Template — Awaiting Initial Definition

---

## Purpose

This document defines the complete component library for Local Latent Containers UI, including:
- Component contracts (props, states, variants)
- Interaction patterns and transitions
- Accessibility requirements
- Usage guidelines

---

## Design Principles

1. **Hierarchy through space and type**, not color
2. **Monochrome chrome**: IKB blue reserved for data/orbs only
3. **Motion as breath**: 120–320ms transitions, one animated region max
4. **Borders over shadows**: hairline borders, no drop shadows
5. **WCAG AA minimum**: All text meets contrast requirements

---

## Core Components

### Button

**Purpose:** Primary and secondary actions

**Variants:**
- `primary`: Ink background, white text (main CTAs)
- `secondary`: White background, ink border (supporting actions)
- `ghost`: Transparent, ink text (tertiary actions)

**Props:**
```typescript
interface ButtonProps {
  variant: 'primary' | 'secondary' | 'ghost';
  size: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  loading?: boolean;
  children: ReactNode;
  onClick: () => void;
}
```

**States:**
- Default: Base styles
- Hover: Scale 1.02, 120ms ease-out
- Active: Y-translate 2px
- Focus: 1px ink focus ring (keyboard)
- Disabled: 40% opacity, no interaction
- Loading: Spinner replaces text, disabled

**Accessibility:**
- Full keyboard support (space/enter)
- ARIA role: button
- ARIA states: aria-disabled, aria-busy

**Motion:**
- Hover: 120ms ease-out
- Active: instant
- Focus: 120ms ease-out

---

### Input.Search

**Intent:** Primary query entry + diagnostics toggle anchor. Maps directly to `SearchRequest.query`.

**Anatomy:** label (optional helper text), input shell, embedded diagnostics toggle (pill) aligned right, 1px hairline border, `--space-4` vertical padding.

**Props:**
```typescript
interface SearchInputProps {
  value: string;
  placeholder?: string;
  diagnosticsEnabled: boolean;
  onToggleDiagnostics(): void;
  onSubmit(value: string): void;
  loading?: boolean; // true while MCP search pending
}
```

**States:** default, hover (border → `--line-2`), focus (border → `--ink-1`, caret `ikb-2`), loading (right-side spinner), error (ember underline + message referencing `issues[]`).

**Interactions:** submit on Enter; pressing ⌘K/CTRL+K focuses. Diagnostics pill displays current mode (`diagnostics.mode`) via uppercase label with `--ikb-1` text.

**A11y:** role `search`, `aria-autocomplete="none"`, togglable button labelled "Toggle diagnostics".

---

### Card.Container

**Purpose:** Container representation in gallery view

**Anatomy:** Card shell (white background, 1px border), header (container name + modality chips), stats row (document count, chunk count, last ingest), action footer (View/Add buttons)

**Props:**
```typescript
interface ContainerCardProps {
  container: {
    id: string;
    name: string;
    theme: string;
    modalities: string[];
    stats: {
      document_count: number;
      chunk_count: number;
      last_ingest: string;
    };
  };
  onSelect: (id: string) => void;
  onAddContent: (id: string) => void;
}
```

**States:**
- Default: Base card styles, subtle border
- Hover: Border darken (line-1 → line-2), 2px lift transform, 120ms ease-out
- Focus: 1px ink focus ring (keyboard navigation)
- Active: Slight scale(0.98) on click

**Layout:**
- Padding: 2.5rem (40px)
- Gap between sections: 1.5rem (24px)
- Modality chips: horizontal flex gap 0.5rem

**A11y:**
- role="article"
- aria-label includes container name and stats
- Full keyboard support (Enter to select, Space to activate buttons)

**Motion:**
- Hover lift: 120ms ease-out
- Focus ring: 120ms ease-out
- Press: instant scale

---

### Modal.Base

**Purpose:** Foundation overlay component for document details, forms, etc.

**Anatomy:** Backdrop (95% white overlay + subtle blur), content panel (white background, 1px ink border, 8px radius), close button (top-right ghost), header slot, body slot, footer slot

**Props:**
```typescript
interface ModalBaseProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  size?: 'sm' | 'md' | 'lg' | 'full';
  children: ReactNode;
  footer?: ReactNode;
  closeOnBackdrop?: boolean;
  closeOnEscape?: boolean;
}
```

**Sizes:**
- sm: 480px max-width
- md: 640px max-width
- lg: 896px max-width
- full: 95vw, 95vh

**States:**
- Closed: opacity 0, pointer-events none
- Open: opacity 1, pointer-events auto
- Backdrop: subtle blur(2px)

**Motion:**
- Open: 280ms cubic-bezier(.34, 1.56, .64, 1) (slight spring)
- Close: 280ms ease-in-out (symmetrical fade)
- Reduced motion: instant opacity change

**A11y:**
- role="dialog"
- aria-modal="true"
- aria-labelledby points to title
- Focus trap within modal
- First focusable element gets focus on open
- Escape key always closes
- Click-away closes (unless form has unsaved changes)

---

### Selector.MultiContainer

**Intent:** Choose one or more containers for search/export; reflects backend `container_ids` array.

**Anatomy:** label, trigger pill showing selected containers count/names, popover panel with search input, list of containers with checkboxes + stats, footer actions (Select all/None, Apply).

**Props:**
```typescript
interface MultiContainerSelectorProps {
  containers: Array<{ id: string; name: string; theme?: string; modalities: string[]; stats?: { documents?: number; chunks?: number } }>;
  selectedIds: string[];
  onChange: (ids: string[]) => void;
  maxVisibleBadges?: number; // default 2, spill into "+N" pill
  disabled?: boolean;
  busy?: boolean; // when fetching containers
  error?: string | null;
}
```

**States:** default, hover (border line-2), focus (ink ring), open (popover visible), busy (spinner in trigger), error (ember underline + helper text), empty (disabled + "No containers" helper).

**Behavior:** clicking trigger opens popover; typing in filter input narrows list by name/theme; checkboxes toggle selection; "Select all" respects filtered list; Apply closes popover and fires onChange. Keyboard: Enter/Space toggles trigger; Arrow keys move through list; Space toggles checkbox; Esc closes; Tab traps within popover.

**Layout:** trigger height 40px min; trigger shows up to `maxVisibleBadges` badges (hairline border pills) with overflow "+N" pill. Popover width 360–420px, padding 16px, list max-height 320px scrollable.

**Motion:** popover fade/scale 0.2s ease; focus/hover 120ms. Reduced motion: instant open/close.

**A11y:** role="combobox" on trigger with `aria-expanded`; popover role="listbox"; checkboxes role="option" with `aria-selected`; all interactive elements 40px hit target; helper text for errors; consistent focus outline.

---

### List.Result

**Intent:** Render `SearchResult` rows with provenance + diagnostics contexts.

**Anatomy:** title row (result.title + score badge), snippet block (clamp 3 lines, `--text-base`), provenance row (uri/domain + ingestion timestamp), diagnostics rail icons (modality chip + dedup badge when `meta.semantic_dedup_score`).

**Props:**
```typescript
interface ResultItemProps {
  result: SearchResult; // direct MCP payload
  diagnosticsVisible: boolean;
  selected?: boolean;
  onSelect?(result: SearchResult): void;
}
```

**States:** default, hover (translateY(-1px) + border emphasize), active (background `--paper-0`), diagnostics (shows timings + container). If `result.meta.semantic_dedup_score` exists, show badge `"dedup"` with score.

**Metrics surfacing:**
- Score badge uses `--ikb-2` text when ≥0.9 else `--ink-2`.
- Latency chips hidden per row; aggregated metrics stay in diagnostics panel.

**A11y:** entire row is button-like; `role="button"`, `aria-pressed` for selection, ensure focus ring 1px.

---

### Chips.Meta

**Purpose:** Inline metadata for modality, dedup state, diagnostics hits.

**Variants:**
- `modality`: text from `result.modality`, uppercase label, fill `--diag-score-pill-bg`.
- `dedup`: shows `≈{score:.2f}` when `semantic_dedup_score` present, stroke `--ikb-0`.
- `issue`: uses ember background for `issues[]` surfaced from SearchResponse.

**Props:**
```typescript
interface MetaChipProps {
  label: string;
  tone: 'neutral' | 'info' | 'warning';
  icon?: ReactNode;
}
```

**States:** default, hover (no fill change), focus (hairline). Minimum height 24px.

---

## Layout Components

### Header

**Purpose:** Global navigation and branding

**Anatomy:** Left (logo/app name), center (search bar when on search page), right (diagnostics toggle, user menu)

**Props:**
```typescript
interface HeaderProps {
  showSearch?: boolean;
  searchValue?: string;
  onSearchChange?: (value: string) => void;
  diagnosticsEnabled?: boolean;
  onToggleDiagnostics?: () => void;
}
```

**Layout:**
- Height: 64px
- Padding: 0 2.5rem
- Search bar: max-width 720px when centered

**States:**
- Default: transparent background
- Scrolled: subtle background (paper-0)

**Motion:**
- Background change: 200ms ease-out
- Search focus: border transitions as per Input.Search

**A11y:**
- role="banner"
- Skip link to main content
- Logical tab order

---

### Sidebar

**Purpose:** Navigation between containers and views

**Anatomy:** Container list, create button, settings link

**Props:**
```typescript
interface SidebarProps {
  containers: Array<{
    id: string;
    name: string;
    active: boolean;
  }>;
  activeContainerId?: string;
  onSelectContainer: (id: string) => void;
  onCreateContainer: () => void;
}
```

**Layout:**
- Width: 280px
- Padding: 2.5rem 1.5rem
- Position: fixed left

**States:**
- Default: background paper-1
- Item hover: background paper-0
- Item active: left border ikb-2, background paper-0

**Motion:**
- Item hover: 120ms ease-out
- Active indicator: 200ms ease-out

**A11y:**
- role="navigation"
- aria-label="Main navigation"
- aria-current="page" for active item

---

### SearchBar

**Purpose:** Wraps Input.Search, container selector, and action buttons

**Anatomy:** 2 columns; left houses Input.Search full width, right column (max 320px) contains diagnostics toggle + golden query shortcut

**Props:**
```typescript
interface SearchBarProps {
  query: string;
  onQueryChange: (value: string) => void;
  onSubmit: () => void;
  diagnosticsEnabled: boolean;
  onToggleDiagnostics: () => void;
  onRunGoldenQueries?: () => void;
  loading?: boolean;
}
```

**Layout:**
- Grid: 1fr auto
- Gap: 1rem
- Right column max-width: 320px

**Interactions:**
- ⌘↩ triggers onRunGoldenQueries
- ⌘K focuses search input
- Ctrl+D toggles diagnostics

**A11y:**
- role="search"
- aria-label="Container search"

---

### Loading.Skeleton

**Purpose:** Placeholder during loading states

**Shapes:** mimic List.Result (title bar, snippet lines)

**Props:**
```typescript
interface SkeletonProps {
  count?: number;
  diagnosticsVisible?: boolean;
}
```

**Style:**
- Hairline borders (line-1)
- Gradient shimmer animation
- Maintain layout (no content shift)

**Motion:**
- Shimmer: 200ms ease-in-out loop
- Reduced motion: static background

**A11y:**
- aria-busy="true"
- aria-label="Loading results"

---

### Error.Banner

**Purpose:** Surface issues[] from MCP responses

**Props:**
```typescript
interface ErrorBannerProps {
  issues: string[];
  onRetry?: () => void;
}
```

**Style:**
- Banner at top (ember border-left, ink text)
- Message: "Search timeout. Showing partial results."
- Action: "Retry" ghost button

**Behavior:**
- Sticky at top of results list
- Auto-dismiss after 10s (with undo)
- Diagnostics rail auto-expands

**A11y:**
- role="alert"
- aria-live="polite"

---

### Empty.State

**Purpose:** Show when no results found

**Props:**
```typescript
interface EmptyStateProps {
  query?: string;
  onClearFilters?: () => void;
  onToggleDiagnostics?: () => void;
}
```

**Content:**
- Icon: outlined orb (monochrome)
- Title: "Nothing surfaced yet"
- Copy: "Try a broader query or disable semantic dedup"

**Actions:**
- Primary: "Clear filters"
- Secondary: "Toggle diagnostics"

**Metrics:**
- Display latest latencies so designer sees pipeline still responded

**A11y:**
- role="status"
- aria-live="polite"

---

## Diagnostics Components

### Diagnostics.Toggle

**Purpose:** Inline pill inside search/header to switch `diagnosticsVisible` state.

**States:** `off` (label “diagnostics”), `on` (label "diagnostics ✓" + `--ikb-1` text). Keyboard `Ctrl+D` toggles.

**A11y:** `aria-pressed` syncs with state; tooltip explains metrics refer to MCP payload.

### Diagnostics.Panel

**Intent:** Visualize `SearchResponse.diagnostics` + `timings_ms` + aggregated summary from golden query script.

**Layout:** fixed 320px column; table with rows: mode, bm25 hits, vector hits, average latency, dedup drops. Use tokens from TOKENS.md.

**Props:**
```typescript
interface DiagnosticsPanelProps {
  diagnostics: SearchResponse['diagnostics'];
  timings: SearchResponse['timings_ms'];
  goldenSummary?: GoldenReport; // from .artifacts file when available
}
```

**Behavior:** Highlight latency budgets using `diagnostics.latency_over_budget_ms` (warn tone + badge if >0) and surface backend issues (e.g., `LATENCY_BUDGET_EXCEEDED`) inline. When `goldenSummary` present, show sparkline (ASCII) referencing aggregated latencies. Panel collapses accordion-style when toggle off.

---

## Document Modal

### Modal.Document

**Intent:** Deep dive into selected chunk/document pair.

**Anatomy:** left column preview (if modality pdf), right column metadata grid (uri, ingestion date, dedup target). Footer has "Open source" ghost button.

**Props:**
```typescript
interface DocumentModalProps {
  result: SearchResult;
  onClose(): void;
}
```

**Interactions:** ESC closes, clicking backdrop closes, but include "Diagnostics" tab referencing panel data (latency, dedup score, MinIO object key).

**Motion:** 280 ms ease-spring open, 200 ms close; respect reduced-motion → fade only.

**A11y:** focus trapped, `aria-labelledby` referencing title, `aria-describedby` referencing provenance.

---

## Component Usage Guidelines

### When to Use Button.Primary
- Main call-to-action on a page/modal
- Only ONE primary button visible at a time
- Example: "Add to Container", "Search", "Save"

### When to Use Button.Secondary
- Supporting actions
- Multiple actions of similar importance
- Example: "Cancel", "Export", "Refresh"

### When to Use Button.Ghost
- Tertiary/destructive actions
- Navigation within card
- Example: "Close", "Dismiss", "View Details"

---

## Accessibility Checklist

- [ ] All interactive elements have min-hit-target 40x40px
- [ ] Full keyboard navigation (tab order logical)
- [ ] Visible focus states (1px ink ring, no glow)
- [ ] ARIA labels on icon-only buttons
- [ ] Color not sole indicator of state (pair with text/icon)
- [ ] Reduced-motion variants (prefers-reduced-motion)
- [ ] Screen reader tested with VoiceOver/NVDA
- [ ] Contrast ratios: text ≥4.5:1, headings ≥7:1

---

## Testing Strategy

### Visual Regression
- Chromatic or Percy for component snapshots
- Test all variants, states, breakpoints

### Interaction Testing
- Cypress or Playwright for user flows
- Keyboard navigation tests
- Screen reader compatibility tests

### Accessibility Testing
- axe-core integration
- Manual WCAG AA audit

---

**Status:** 🟡 In Progress  
**Next Action:** Flesh out PATTERNS + accessibility specs for remaining components  
**Cross-Reference:** TOKENS.md, PATTERNS.md, ACCESSIBILITY.md
