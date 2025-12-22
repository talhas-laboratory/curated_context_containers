import { act, renderHook, waitFor } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import { server } from '../../tests/msw/server';
import { createTestQueryClient } from '../../tests/utils';
import { useCreateContainer, useDescribeContainer, useListContainers } from './use-containers';

function createWrapper() {
  const queryClient = createTestQueryClient();
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe('useListContainers', () => {
  it('returns active containers', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useListContainers('active'), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.containers).toHaveLength(1);
    expect(result.current.data?.containers[0].name).toBe('Expressionist Art');
  });

  it('handles empty state', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useListContainers('empty'), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.containers).toHaveLength(0);
  });

  it('surfaces errors', async () => {
    server.use(
      http.post('*/v1/containers/list', () =>
        new HttpResponse(JSON.stringify({ error: { code: 'SERVER_ERROR', message: 'fail' } }), { status: 500 })
      )
    );
    const wrapper = createWrapper();
    const { result } = renderHook(() => useListContainers('active'), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect((result.current.error as Error).message).toContain('fail');
  });
});

describe('useDescribeContainer', () => {
  it('returns container detail', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useDescribeContainer('container-1'), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.container.id).toBe('container-1');
    expect(result.current.data?.request_id).toBe('req-123');
  });

  it('handles not found', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useDescribeContainer('missing'), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect((result.current.error as Error).message).toContain('not found');
  });
});

describe('useCreateContainer', () => {
  it('creates a container with defaults', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useCreateContainer(), { wrapper });

    let response: any;
    await act(async () => {
      response = await result.current.mutateAsync({
        name: 'container-new',
        theme: 'New experiments',
      });
    });

    expect(response.success).toBe(true);
    expect(response.container_id).toBe('container-new');
  });

  it('surfaces validation errors', async () => {
    const wrapper = createWrapper();
    const { result } = renderHook(() => useCreateContainer(), { wrapper });

    await act(async () => {
      await expect(
        result.current.mutateAsync({
          // @ts-expect-error intentionally invalid to trigger 400
          name: '',
          theme: '',
        })
      ).rejects.toMatchObject({ message: expect.stringMatching(/name required/i) });
    });
  });
});
