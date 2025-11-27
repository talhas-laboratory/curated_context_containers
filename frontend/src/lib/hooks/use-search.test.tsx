import { renderHook } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { createTestQueryClient } from '../../tests/utils';
import { useSearch } from './use-search';

function createWrapper() {
  const queryClient = createTestQueryClient();
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe('useSearch', () => {
  it('returns results with diagnostics', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useSearch(), { wrapper });

    const response = await result.current.mutateAsync({
      query: 'smoke',
      containerIds: ['container-1'],
      diagnostics: true,
      mode: 'hybrid',
      k: 5,
    });

    expect(response.results).toHaveLength(1);
    expect(response.diagnostics.mode).toBe('hybrid');
    expect(response.timings_ms.total_ms).toBeGreaterThan(0);
  });

  it('handles empty hits and surfaces issues', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useSearch(), { wrapper });

    const response = await result.current.mutateAsync({
      query: 'empty',
      containerIds: ['container-1'],
    });

    expect(response.results).toHaveLength(0);
    expect(response.issues).toContain('NO_HITS');
    expect(response.partial ?? false).toBe(false);
  });

  it('throws on error response', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useSearch(), { wrapper });

    await expect(
      result.current.mutateAsync({
        query: 'error',
        containerIds: ['container-1'],
      })
    ).rejects.toMatchObject({ code: 'NO_HITS' });
  });
});
