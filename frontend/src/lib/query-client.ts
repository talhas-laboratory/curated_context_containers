/**
 * React Query Client Configuration
 * 
 * Singleton QueryClient with sensible defaults for MCP API:
 * - 30s staleTime for list/describe (containers don't change often)
 * - 1 retry for transient failures
 * - Error logging hook
 */

import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30 * 1000, // 30 seconds
      retry: 1,
      refetchOnWindowFocus: false,
      refetchOnReconnect: true,
    },
    mutations: {
      retry: 1,
    },
  },
});

// Error logging hook (can be extended with toast notifications)
queryClient.getQueryCache().subscribe((event) => {
  if (event?.type === 'updated' && event.query.state.status === 'error') {
    const error = event.query.state.error;
    if (error) {
      console.error('[React Query Error]', {
        queryKey: event.query.queryKey,
        error,
      });
    }
  }
});
