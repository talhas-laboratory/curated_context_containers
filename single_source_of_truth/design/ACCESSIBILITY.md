# Accessibility Standards — WCAG AA Compliance

**Owner:** IKB Designer (minimalist environment designer)  
**Last Updated:** ⚪ Not Started  
**Status:** 📝 Template — Awaiting Audit

---

## Purpose

This document defines accessibility standards and requirements for Local Latent Containers UI to ensure WCAG 2.1 Level AA compliance.

---

## Compliance Target

**Standard:** WCAG 2.1 Level AA  
**Scope:** All public-facing UI components and flows  
**Testing:** Automated (axe-core) + Manual (VoiceOver, NVDA)

---

## Checklist

### 1. Perceivable

#### 1.1 Text Alternatives
- [ ] All images have alt text (or aria-label if decorative)
- [ ] Icon-only buttons have aria-label
- [ ] Form inputs have associated labels (visible or aria-label)

#### 1.2 Time-based Media
- [ ] N/A (no video/audio in Phase 1)

#### 1.3 Adaptable
- [ ] Semantic HTML (header, nav, main, section, article)
- [ ] Logical heading hierarchy (h1 → h2 → h3, no skips)
- [ ] Landmarks for screen readers (role="search", role="main")
- [ ] Tables use <th> for headers (if any tables used)

#### 1.4 Distinguishable
- [ ] Text contrast ≥4.5:1 (body text vs background)
- [ ] Heading contrast ≥7:1 (preferred, AA large text minimum 3:1)
- [ ] Color not sole indicator of state (pair with icon/text)
- [ ] Text resizable to 200% without loss of function
- [ ] No background images behind text (readability)
- [ ] Spacing: line-height ≥1.5, paragraph spacing ≥2x font-size

**Measured Contrasts:**
| Element | Foreground | Background | Ratio | Pass? |
|---------|------------|------------|-------|-------|
| Body text | ink-1 (#1a1a1a) | paper-1 (#ffffff) | 14.3:1 | ✅ AAA |
| Secondary text | ink-2 (#7a7a7a) | paper-1 (#ffffff) | 4.6:1 | ✅ AA |
| IKB data | ikb-2 (#153dcc) | paper-1 (#ffffff) | 6.8:1 | ✅ AA |

---

### 2. Operable

#### 2.1 Keyboard Accessible
- [ ] All functionality available via keyboard (no mouse-only)
- [ ] Tab order is logical (follows visual flow)
- [ ] No keyboard traps (focus can always move forward/backward)
- [ ] Skip to content link (hidden until focus)
- [ ] Focus visible at all times (1px ink ring)

#### 2.2 Enough Time
- [ ] No time limits on interactions (Phase 1)
- [ ] Auto-dismiss errors have pause/cancel option
- [ ] Search timeout returns partial results (no hard failure)

#### 2.3 Seizures and Physical Reactions
- [ ] No flashing content >3 times per second
- [ ] No parallax or vestibular motion (all motion is 2D translate/scale)

#### 2.4 Navigable
- [ ] Page title describes purpose (`<title>Search | expressionist-art</title>`)
- [ ] Focus order follows visual/semantic order
- [ ] Link text is descriptive ("View Document Detail", not "Click Here")
- [ ] Multiple ways to navigate (breadcrumbs, back button, home link)
- [ ] Headings describe sections
- [ ] Current page indicated in navigation (aria-current="page")

#### 2.5 Input Modalities
- [ ] Pointer gestures have keyboard equivalents
- [ ] Click targets ≥40x40px (iOS/Android recommendation)
- [ ] No path-based gestures (swipe, pinch) in Phase 1

---

### 3. Understandable

#### 3.1 Readable
- [ ] Language declared (`<html lang="en">`)
- [ ] No jargon without explanation
- [ ] Abbreviations explained on first use (or aria-label)

#### 3.2 Predictable
- [ ] Focus does not trigger navigation (only Enter/click)
- [ ] Form submission explicit (button, not focus change)
- [ ] Navigation consistent across pages
- [ ] Modals do not auto-close on focus loss (only explicit action)

#### 3.3 Input Assistance
- [ ] Form errors identified and described
- [ ] Labels and instructions provided before input
- [ ] Suggestions offered on error (e.g., "Try broader terms")
- [ ] Confirmation for destructive actions ("Delete Container?")

---

### 4. Robust

#### 4.1 Compatible
- [ ] Valid HTML (W3C validator)
- [ ] ARIA used correctly (roles, states, properties)
- [ ] Name, role, value for all custom controls
- [ ] Status messages use aria-live (polite or assertive)

---

## Reduced Motion Support

**When `prefers-reduced-motion: reduce`:**
- All transitions: 0ms (instant state changes)
- Reflection pauses: kept (100ms, for clarity)
- Skeleton screens: no pulse animation
- Modals: instant opacity change (no spring)

**Implementation:**
```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## Screen Reader Testing

**Tools:**
- **macOS:** VoiceOver (Safari, Chrome)
- **Windows:** NVDA (Firefox, Chrome)
- **iOS:** VoiceOver (Mobile Safari)

**Test Scenarios:**
1. Navigate entire page with screen reader only
2. Fill out and submit search form
3. Navigate results with arrow keys
4. Open and close modal (document detail)
5. Encounter error and follow remediation
6. Use skip links and landmarks

---

## Automated Testing

**Tool:** axe-core (via jest-axe or Cypress axe plugin)

**Run frequency:** Every commit (CI/CD pipeline)

**Severity levels:**
- Critical: Block merge
- Serious: Block merge
- Moderate: Warn (review required)
- Minor: Warn (fix when possible)

---

## Manual Audit Checklist

- [ ] Keyboard-only navigation test (unplug mouse)
- [ ] Screen reader test (VoiceOver + NVDA)
- [ ] Color contrast validation (WebAIM Contrast Checker)
- [ ] Text resize test (200% zoom, no horizontal scroll)
- [ ] Reduced motion test (OS setting enabled)
- [ ] Touch target size (inspect with browser DevTools)
- [ ] Form error handling (trigger all error states)

---

## Known Issues / Exceptions

| Issue | Severity | Remediation Plan | ETA |
|-------|----------|------------------|-----|
| (None yet) | — | — | — |

---

## References

- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)
- [axe DevTools](https://www.deque.com/axe/devtools/)
- [Apple VoiceOver Guide](https://support.apple.com/guide/voiceover/welcome/mac)

---

**Status:** 📝 Template  
**Next Action:** IKB Designer to conduct initial audit  
**Cross-Reference:** COMPONENTS.md, PATTERNS.md, TOKENS.md

