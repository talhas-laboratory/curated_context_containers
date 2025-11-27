/**
 * Motion utilities with reduced-motion support
 */

/**
 * Check if user prefers reduced motion
 */
export function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined') {
    return false;
  }
  const mediaQuery = typeof window.matchMedia === 'function'
    ? window.matchMedia('(prefers-reduced-motion: reduce)')
    : null;
  return !!mediaQuery && mediaQuery.matches;
}

/**
 * Get animation duration respecting reduced motion
 */
export function getDuration(baseDuration: number): number {
  return prefersReducedMotion() ? 0 : baseDuration;
}

/**
 * Motion tokens (from design system)
 */
export const motionTokens = {
  duration: {
    instant: 0,
    fast: 120,
    base: 200,
    slow: 280,
    deliberate: 320,
  },
  easing: {
    linear: 'linear',
    easeIn: 'ease-in',
    easeOut: 'ease-out',
    easeInOut: 'ease-in-out',
    spring: 'cubic-bezier(.34, 1.56, .64, 1)',
  },
} as const;

/**
 * Get motion props for framer-motion with reduced-motion support
 */
export function getMotionProps(
  duration: number = motionTokens.duration.base,
  easing: string = motionTokens.easing.easeOut
) {
  const actualDuration = getDuration(duration);
  return {
    transition: {
      duration: actualDuration / 1000, // Convert to seconds
      ease: easing,
    },
  };
}
