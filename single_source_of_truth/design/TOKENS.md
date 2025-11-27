# Design Tokens — Visual System

**Owner:** IKB Designer (minimalist environment designer)  
**Last Updated:** ⚪ Not Started  
**Status:** 🟡 Partially Defined (from agent spec)

---

## Purpose

This document defines the complete design token system for Local Latent Containers UI, including:
- Color palette (neutrals + IKB accent)
- Typography scale
- Spacing system (4px grid)
- Motion timings and easings
- Material properties (borders, surfaces)

---

## Color Tokens

### Neutrals (Monochrome Chrome)
```css
--paper-0: #fafaf8;     /* Background wash */
--paper-1: #ffffff;     /* Card surfaces */
--ink-1: #1a1a1a;       /* Primary text, borders */
--ink-2: #7a7a7a;       /* Secondary text, placeholders */
--line-1: rgba(0,0,0,.06);  /* Subtle dividers */
--line-2: rgba(0,0,0,.12);  /* Emphasized borders */
```

**Usage:**
- `paper-0`: Page background
- `paper-1`: Card, modal, elevated surfaces
- `ink-1`: Headings, body text, primary borders
- `ink-2`: Labels, captions, disabled text
- `line-1`: Hairline dividers (default state)
- `line-2`: Borders on focus/hover

### IKB Spectrum (Data + Orbs Only)
```css
--ikb-0: #001a66;       /* Darkest (data shadows) */
--ikb-1: #0a2ea6;       /* Data visualization */
--ikb-2: #153dcc;       /* Orbs, data points */
--ikb-3: #2956ff;       /* Brightest (active data) */
```

**Usage:**
- **NEVER** use for chrome, buttons, backgrounds
- **ONLY** use for: search result scores, data orbs, provenance indicators, diagnostics charts

### Diagnostics Tokens
```css
--diag-panel-bg: rgba(0, 0, 0, 0.02);
--diag-panel-border: rgba(0, 0, 0, 0.08);
--diag-latency-good: var(--ikb-2);
--diag-latency-warn: var(--ember);
--diag-score-pill-bg: rgba(0, 0, 0, 0.04);
--diag-score-pill-text: var(--ink-1);
--diag-hits-pill-bg: rgba(0, 0, 0, 0.06);
--diag-hits-pill-text: var(--ink-2);
```

**Mapping to payloads:**
- `SearchResponse.timings_ms.vector_ms`/`bm25_ms` drive latency pills; compare against thresholds (good ≤450 ms → `--diag-latency-good`, warning ≥700 ms → `--diag-latency-warn`).
- `diagnostics.bm25_hits`/`vector_hits` render as count chips using `--diag-hits-pill-*`.
- `results[*].score` surfaces in score badges colored by `--diag-score-pill-*` with `ikb-2` stroke when ≥0.9.
- `diagnostics.latency_over_budget_ms > 0` flips diagnostic text/buttons to `--diag-latency-warn` to mirror backend `LATENCY_BUDGET_EXCEEDED` issue.

### Accent (Decision Heat)
```css
--ember: #ff7a1a;       /* Error states, destructive actions */
```

**Usage:**
- Error messages
- Destructive confirmations ("Delete", "Clear")
- Threshold warnings (e.g., "Low quality results")

---

## Typography

### Font Stack
```css
--font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
```

### Type Scale
```css
--text-xs: 0.70rem;     /* Micro labels, metadata */
--text-sm: 0.85rem;     /* Secondary text, captions */
--text-base: 1.00rem;   /* Body text (15–16px) */
--text-lg: 1.25rem;     /* Subheadings */
--text-xl: 1.75rem;     /* Headings */
--text-2xl: 2.25rem;    /* Page titles */
```

### Line Heights
```css
--leading-tight: 1.25;   /* Headings */
--leading-normal: 1.5;   /* Body text */
--leading-relaxed: 1.75; /* Long-form content */
```

### Font Weights
```css
--weight-light: 300;     /* Headings (calm, spacious) */
--weight-normal: 400;    /* Body text */
--weight-medium: 500;    /* Emphasis within body */
--weight-bold: 600;      /* Rare use (data labels) */
```

### Letter Spacing
```css
--tracking-tight: -0.02em;   /* Large headings */
--tracking-normal: 0;        /* Body text */
--tracking-wide: 0.08em;     /* Uppercase labels */
--tracking-wider: 0.12em;    /* Micro labels (all-caps) */
```

**Typography Rules:**
- Headings: weight-light (300), tracking-tight
- Body: weight-normal (400), leading-normal
- Labels: text-xs, uppercase, tracking-wider

---

## Spacing System (4px Grid)

### Base Unit
```css
--unit: 4px;
```

### Spacing Scale
```css
--space-1: 4px;      /* 1 unit (tight) */
--space-2: 8px;      /* 2 units */
--space-3: 12px;     /* 3 units */
--space-4: 16px;     /* 4 units (common) */
--space-5: 20px;     /* 5 units */
--space-6: 24px;     /* 6 units */
--space-8: 32px;     /* 8 units (sections) */
--space-10: 40px;    /* 10 units (card padding) */
--space-12: 48px;    /* 12 units (gaps) */
--space-16: 64px;    /* 16 units (section breaks) */
--space-20: 80px;    /* 20 units (large breaks) */
```

**Usage Guidelines:**
- Card padding: `--space-10` (40px minimum)
- Element gaps: `--space-12` to `--space-16` (48–64px)
- Section breaks: `--space-16` to `--space-20` (64–80px)
- Inline spacing: `--space-2` to `--space-4` (8–16px)
- Diagnostics rail: `--space-6` vertical padding, `--space-4` row spacing to keep latency badges legible next to metrics table.

---

## Motion System

### Duration Tokens
```css
--duration-instant: 0ms;      /* State changes (disabled) */
--duration-fast: 120ms;       /* Hover, focus */
--duration-base: 200ms;       /* Default transitions */
--duration-slow: 280ms;       /* Modals, context switches */
--duration-deliberate: 320ms; /* Search submit (w/ pause) */
```

### Easing Tokens
```css
--ease-linear: linear;
--ease-in: ease-in;
--ease-out: ease-out;
--ease-in-out: ease-in-out;
--ease-spring: cubic-bezier(.34, 1.56, .64, 1);  /* Modal open */
```

### Motion Table
| Interaction | Duration | Easing | Notes |
|-------------|----------|--------|-------|
| Hover | 120ms | ease-out | Button, card lift |
| Focus | 120ms | ease-out | Keyboard nav |
| Active | instant | — | Button press |
| Modal open | 280ms | ease-spring | Slight overshoot |
| Modal close | 280ms | ease-in-out | Symmetrical |
| Search submit | 320ms | ease-in-out | + 100ms pause |
| Diagnostics pulse | 8s | sine | Subtle attention |

**Motion Rules:**
- Max one animated region per view
- Respect `prefers-reduced-motion` (instant state changes)
- Reflection pauses: 80–120ms before showing results
- Diagnostics row flip (when payload updates): fade/slide 160 ms, triggered only when `diagnostics.mode` changes.

---

## Material Properties

### Surfaces
```css
--surface-matte: background with subtle grain (≤1% opacity);
--surface-paper: white (#ffffff), no texture;
--surface-diagnostics: linear-gradient(180deg, rgba(0,0,0,0.01), rgba(0,0,0,0))
```

### Borders
```css
--border-hairline: 1px solid var(--line-1);
--border-emphasized: 1px solid var(--line-2);
--border-focus: 1px solid var(--ink-1);  /* Keyboard focus */
--border-diagnostics: 1px solid var(--diag-panel-border);
```

### Border Radius
```css
--radius-none: 0px;       /* Default (sharp corners) */
--radius-sm: 4px;         /* Chips, small elements */
--radius-md: 8px;         /* Cards, modals */
--radius-full: 9999px;    /* Pills, orbs */
```

**Material Rules:**
- No drop shadows (borders only)
- Hairline borders by default
- Emphasized borders on hover/focus
- Subtle background grain (≤1% opacity) on chrome surfaces

---

## Elevation System (No Shadows)

| Level | Technique | Example |
|-------|-----------|---------|
| 0 | Baseline (paper-0) | Page background |
| 1 | White surface + hairline border | Cards |
| 2 | Darker border (line-2) | Hover state |
| 3 | Transform (2px lift) | Active state |
| 4 | Overlay (95% white + blur) | Modals |

**No box-shadow used** — elevation communicated through border weight and subtle transforms.

---

## Breakpoints

```css
--breakpoint-sm: 640px;   /* Mobile landscape */
--breakpoint-md: 768px;   /* Tablet */
--breakpoint-lg: 1024px;  /* Laptop */
--breakpoint-xl: 1280px;  /* Desktop */
--breakpoint-2xl: 1536px; /* Large desktop */
```

**Target:** Desktop-first (MacBook Air M2 @ 1440x900 native, 2880x1800 Retina)

---

## Grid System

**Base:** 4px unit  
**Column count:** Fluid (no fixed columns)  
**Gaps:** 48–64px between major sections  
**Max width:** 1280px (content well)  
**Diagnostics rail:** fixed 320px column hugging right edge when toggle enabled; collapses to 0 with motion token `--duration-base`.

---

## Data Token Map

| Payload Field | Token | Notes |
|---------------|-------|-------|
| `timings_ms.vector_ms` | `--diag-latency-good` / `--diag-latency-warn` | Compare to 450 ms / 700 ms thresholds |
| `timings_ms.bm25_ms` | same as above | Displayed in diagnostics rail |
| `diagnostics.mode` | `--ikb-1` text accent | Label for “Hybrid / Semantic / BM25” |
| `diagnostics.vector_hits` | `--diag-hits-pill-bg` | Count pill background |
| `results[].score` | `--ikb-0` stroke when ≥0.9 | Highlights highly relevant chunks |
| `results[].provenance.ingested_at` | `--ink-2` timestamp text | Keep provenance subdued |

---

**Status:** 🟡 Partially Defined  
**Next Action:** IKB Designer to validate and extend tokens  
**Cross-Reference:** COMPONENTS.md, PATTERNS.md
