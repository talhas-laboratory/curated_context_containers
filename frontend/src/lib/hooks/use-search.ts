/**
 * React Query hooks for search operations
 */

import { useMutation, useQuery, UseQueryOptions } from '@tanstack/react-query';
import { MCPError, post } from '../mcp-client';
import type { SearchRequest, SearchResponse } from '../types';

export interface UseSearchParams {
  query: string;
  containerIds: string[];
  mode?: 'semantic' | 'hybrid' | 'bm25';
  k?: number;
  diagnostics?: boolean;
}

/**
 * Search hook using mutation (since search is typically triggered by user action)
 */
export function useSearch() {
  return useMutation<SearchResponse, MCPError, UseSearchParams>({
    mutationFn: async (params) => {
      const request: SearchRequest = {
        query: params.query,
        container_ids: params.containerIds,
        mode: params.mode || 'hybrid',
        k: params.k || 10,
        diagnostics: params.diagnostics ?? false,
        rerank: false,
      };
      const response = await post<SearchResponse>('/v1/search', request);
      return response;
    },
  });
}

/**
 * Alternative: Search as query (for preloading or URL-based searches)
 */
export function useSearchQuery(
  params: UseSearchParams | null,
  options?: Omit<UseQueryOptions<SearchResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery<SearchResponse, MCPError>({
    queryKey: ['search', params],
    queryFn: async () => {
      if (!params) {
        throw new Error('Search params required');
      }
      const request: SearchRequest = {
        query: params.query,
        container_ids: params.containerIds,
        mode: params.mode || 'hybrid',
        k: params.k || 10,
        diagnostics: params.diagnostics ?? false,
        rerank: false,
      };
      const response = await post<SearchResponse>('/v1/search', request);
      return response;
    },
    enabled: !!params && !!params.query && params.containerIds.length > 0,
    staleTime: 0, // Search results should always be fresh
    ...options,
  });
}
