/**
 * Design tokens used across the sandbox UI.
 * These are intentionally simple string helpers so components stay consistent.
 */

export const layoutTokens = {
  pageMaxWidth: 'max-w-[1400px]',
  sidebarWidth: 'w-72',
  shellPadding: 'px-6 py-8 lg:px-10',
} as const;

export const typographyTokens = {
  microLabel: 'text-[0.65rem] uppercase tracking-[0.14em] text-ink-2',
  subtle: 'text-sm text-ink-2',
  headline: 'text-3xl font-light text-ink-1',
} as const;

export const surfaceTokens = {
  card: 'rounded-2xl border border-line-1 bg-paper-1',
  mutedCard: 'rounded-2xl border border-line-2 bg-paper-0',
} as const;

export const chipTokens = {
  base: 'rounded-full border border-line-2 bg-paper-0 px-3 py-1 text-xs uppercase tracking-[0.1em] text-ink-2',
  accent: 'rounded-full border border-ink-1 text-ink-1 px-3 py-1 text-xs uppercase tracking-[0.1em]',
} as const;

export const motionDurations = {
  hover: 120,
  context: 280,
} as const;

