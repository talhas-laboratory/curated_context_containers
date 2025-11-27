import '@testing-library/jest-dom/vitest';
import { afterAll, afterEach, beforeAll, vi } from 'vitest';
import { server } from './msw/server';
import { resetDocumentFixtures } from './msw/handlers';

// Polyfill matchMedia for motion utilities and responsive checks
if (typeof window !== 'undefined') {
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

beforeAll(() => server.listen());
afterEach(() => {
  resetDocumentFixtures();
  server.resetHandlers();
});
afterAll(() => server.close());
