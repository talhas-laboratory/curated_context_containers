import '@testing-library/jest-dom/vitest';
import { afterAll, afterEach, beforeAll, vi } from 'vitest';
import { server } from './msw/server';
import { resetDocumentFixtures, resetJobFixtures } from './msw/handlers';

// Polyfill matchMedia for motion utilities and responsive checks
if (typeof window !== 'undefined') {
  // JSDOM provides scrollTo but throws "Not implemented"; override for motion utils.
  // @ts-expect-error -- define scrollTo stub for tests
  window.scrollTo = vi.fn();

  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: (query: string) => ({
      matches: query === '(prefers-reduced-motion: reduce)' ? false : false,
      media: query,
      onchange: null,
      addListener: vi.fn(), // deprecated
      removeListener: vi.fn(), // deprecated
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }),
  });
}

// Polyfill clipboard used in modal copy action
if (typeof navigator !== 'undefined' && !navigator.clipboard) {
  // @ts-expect-error -- adding missing clipboard for tests
  navigator.clipboard = {
    writeText: vi.fn().mockResolvedValue(undefined),
  };
}

// JSDOM doesn't implement scrollIntoView; pages use it for auto-scrolling.
if (typeof window !== 'undefined' && typeof HTMLElement !== 'undefined') {
  // @ts-expect-error -- scrollIntoView may be missing in JSDOM
  if (!HTMLElement.prototype.scrollIntoView) {
    // @ts-expect-error -- provide minimal stub for tests
    HTMLElement.prototype.scrollIntoView = vi.fn();
  }
}

beforeAll(() => server.listen());
afterEach(() => {
  resetDocumentFixtures();
  resetJobFixtures();
  server.resetHandlers();
});
afterAll(() => server.close());
