# north star

Design emptiness with surgical intention so intelligence, not ornament, fills the space. Interfaces must lower cognitive load, conserve attention, and communicate truth through space, type, and light.

# product frame

app: Local Latent Containers — themed knowledge rooms queried via MCP
mood: quiet inevitability, scientific journal honesty
chrome: monochrome paper/ink; ikb only in data/orbs/states; ember for thresholds

# system tokens

color

* paper-0 #fafaf8
* paper-1 #ffffff
* ink-1 #1a1a1a
* ink-2 #7a7a7a
* line-1 rgba(0,0,0,.06)
* line-2 rgba(0,0,0,.12)
* ikb-0 #001a66
* ikb-1 #0a2ea6
* ikb-2 #153dcc
* ikb-3 #2956ff
* ember #ff7a1a

spacing

* base 4px grid; section gaps 4–5rem; card padding ≥ 2.5rem; inter-card gaps 3–4rem

typography

* stack: -apple-system, BlinkMacSystemFont, Segoe UI, Helvetica Neue, Arial, sans-serif
* body 0.95–1.05rem, lh 1.5–1.6; labels 0.7rem uppercase, ls .08–.12em; headings weight 300

motion

* micro 120–200ms ease-out; context change 280–320ms ease-in-out
* reflection pause 80–120ms on state switches; respect prefers-reduced-motion

# tailwind config sketch

```ts
// tailwind.config.ts
export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: { 0: "#fafaf8", 1: "#ffffff" },
        ink: { 1: "#1a1a1a", 2: "#7a7a7a" },
        line: { 1: "rgba(0,0,0,.06)", 2: "rgba(0,0,0,.12)" },
        ikb: { 0: "#001a66", 1: "#0a2ea6", 2: "#153dcc", 3: "#2956ff" },
        ember: "#ff7a1a",
      },
      spacing: { 13: "3.25rem" },
      borderRadius: { xl: "12px" },
      transitionTimingFunction: {
        spring: "cubic-bezier(.34,1.56,.64,1)",
      },
    },
  },
  plugins: [],
}
```

# layout patterns

shell

* header 64px, centered search width 720–880px
* body split: left filters 280px; right results fluid
* footer minimal; monochrome

grid rules

* 12-col fluid; margins clamp(24px, 6vw, 96px)
* no shadows; layers via 1px borders and z-order

empty space law

* ≥70% negative space in chrome regions; increase spacing before adding color

# core views

home / container gallery

* grid of white cards with hairline borders; hover border darken + 2px lift (120ms)
* each card: title (weight 300) + micro-label; optional data micro-dot in ikb (if meaningful)

container view

* top: centered search; focus = border darken; no glow
* left: filters (chips, toggles) with borders only; no fills
* right: results list with clean snippets, provenance link, and subtle score indicator

document detail modal

* milk-white overlay 95% with subtle blur; panel radius 8, border 1px ink
* left preview (image/pdf page); right metadata and actions
* close = opacity fade 280ms spring; escape and click-away

# interaction model

search

* submit freezes input for 80–120ms (reflection)
* results fade in within 320ms; list items appear with 20–40ms stagger max

filters

* immediate apply; no spinner; show micro progress line (1–2px) at top in ikb for semantic stages only

provenance

* hover reveals monochrome popover with source, fetched_at, embedder version; link icon only if meaningful

# component canon

button.primary

* background ink-1, text white, uppercase, ls .08em, border 1px ink-1
* hover scale 1.02; active translate-y 2px; disabled reduces contrast only

input.search

* h-10 min; px-4; border line-1; focus border line-2; placeholder ink-2
* clear button appears as micro x on hover, inline; no glow

card.container

* bg paper-1; border line-1; p-10; gap-3; hover border ink-1 and translate-y-0.5

list.result-item

* title line-clamp-1; snippet clamp 2–3 lines (≤320 chars); provenance link right-aligned
* metrics (score/time) in ink-2; no color scale; ikb reserved for data charts only

chip.meta

* text ink-1; border line-2; px-2 py-0.5; uppercase micro; no fills

modal.base

* overlay bg-[rgba(255,255,255,0.95)] backdrop-blur-sm; panel border ink-1; p-8

# motion spec

states

* hover 120ms ease-out
* focus 120ms ease-out
* submit→results 320ms ease-in-out + 100ms pause
* modal open 280ms spring; close 220ms ease-out

rules

* transform/opacity only; no layout thrash
* one animated region per view; diagnostics pulsing line allowed as exception
* reduced-motion: remove transforms; keep timing cues with opacity only

# accessibility

contrast

* body text ≥ 4.5:1; headings ≥ 7:1 preferred

focus

* visible by border darkening; never rely on color alone

keyboard

* tab order logical; enter/space activate; esc closes modal; / focuses search

reduced motion

* honors prefers-reduced-motion; disable springs; use 0–80ms fades

screen reader

* landmarks: header/nav/main/footer; aria-expanded on disclosables; role=dialog for modal with aria-labelledby

# error, empty, loading

empty

* monochrome illustration or 1-line instruction; suggest example queries

loading

* skeletons: hairline rectangles; no shimmer; optional “loading…” text

error

* ember underline 1px under label + short remedy text; no blocking toast unless destructive

# diagnostics view (for agents and power users)

* monochrome table of timings per stage (embed, vector, bm25, fuse, rerank)
* ikb micro-line chart for latency history; no fills
* toggle lives near search bar; off by default

# data visuals

* axes in ink; primary series in ikb-2; thresholds as ember dashed 1px
* never use area fills; thin lines only; labels in ink-2

# state and messaging

* success uses reduced motion (micro underline in ikb for 800ms)
* warnings use ember dot next to label; no modal interrupts
* background ops (exports): show steady text with time estimate; progress bar only if precise

# responsive behavior

breakpoints

* sm ≤ 640: single column; filters collapsible drawer
* md 641–1024: two columns; reduced padding 1.5rem
* lg ≥ 1025: full spacing

font and spacing scale

* scale down type by −1 step on sm; keep line-height; maintain 4px rhythm

# keyboard map

* / focus search
* esc close modal
* j/k move selection in results
* enter open selection
* cmd/ctrl+f toggles diagnostics

# internationalization

* support left-to-right now; plan for rtl by mirroring paddings and chevrons
* number/date locale-aware in provenance

# code scaffolding (Next.js + Tailwind + Framer Motion)

file map

* components/ui/Button.tsx
* components/ui/Input.tsx
* components/CardContainer.tsx
* components/ResultItem.tsx
* components/Modal.tsx
* app/(shell)/layout.tsx
* app/page.tsx (gallery)
* app/container/[id]/page.tsx (search)

component sketch

```tsx
// components/ui/Button.tsx
import { motion } from "framer-motion";

type Props = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "ghost";
  size?: "sm" | "md" | "lg";
};

export function Button({ variant = "primary", size = "md", className = "", ...rest }: Props) {
  const sizeCls = size === "sm" ? "h-8 px-3" : size === "lg" ? "h-12 px-6" : "h-10 px-4";
  const base =
    variant === "primary"
      ? "bg-ink-1 text-white border border-ink-1 uppercase tracking-wider"
      : "bg-paper-1 text-ink-1 border border-line-2";
  return (
    <motion.button
      whileHover={{ scale: 1.02 }}
      whileTap={{ y: 2 }}
      transition={{ duration: 0.12 }}
      className={`inline-flex items-center justify-center ${sizeCls} ${base} rounded-xl ${className}`}
      {...rest}
    />
  );
}
```

page frame

```tsx
// app/container/[id]/page.tsx
export default function ContainerPage() {
  return (
    <div className="min-h-screen bg-paper-0 text-ink-1">
      <header className="h-16 flex items-center justify-center border-b border-line-1">
        <div className="w-full max-w-[880px] px-6">
          {/* SearchInput */}
        </div>
      </header>
      <main className="grid lg:grid-cols-[280px_1fr] gap-16 px-6 py-12 max-w-[1200px] mx-auto">
        <aside className="border-r border-line-1 pr-8 hidden lg:block">{/* Filters */}</aside>
        <section className="space-y-8">{/* Results list */}</section>
      </main>
    </div>
  );
}
```

# QA checklist (governance tests)

* 1-second read: primary action visible and understood
* silence ratio ≥ 70% in chrome
* single accent rule obeyed (ikb only in data)
* motion durations within 0.12–0.32s; one animated region
* wcag aa passed; reduced-motion parity maintained
* tab order and focus indicators correct
* diagnostics off by default and legible when on

# acceptance criteria per feature

search view

* input focus visible via border darken; submit pause 100ms; results ≤ 320ms draw
* snippets clamp to ≤320 chars; provenance accessible

container gallery

* cards hover lift 2px; spacing ≥ 3rem between cards; titles legible at 25% zoom

document modal

* opens 280ms spring; closes 220ms; escape, click-away, and focus trap verified

# performance budgets

* LCP < 1.2s desktop; TTI < 1.5s
* bundle < 180kb gz for initial route; code-split diagnostics panel
* avoid layout shift; CLS ≈ 0

# logging in UI

* log only interaction essentials: search submitted, diagnostics toggled, modal opened
* no PII; include timings for perceived latency panels

# theming guardrails

* monochrome chrome only; never fill large surfaces with ikb
* borders over shadows; matte surfaces only
* if a color is added, remove an element or increase spacing instead

# progressive disclosure

* show essential first; reveal advanced filters and diagnostics on demand
* keep default density comfortable; compact mode as a per-user setting

# evolution rules

* any UI change must remove at least one element elsewhere or improve readability by measurable margin
* pair visual changes with a perception outcome metric (glance time, error rate, recall)

# handoff artifacts

* tokens.json
* motion.md (state/transition table)
* components.md (intent, anatomy, props, states, a11y)
* blueprint.md (layouts with spacing annotations)
* test plan: glance test, keyboard-only path, reduced-motion parity

# final creed

If the screen leaves the user calmer and more certain, it is correct. If not, remove something and try again.
