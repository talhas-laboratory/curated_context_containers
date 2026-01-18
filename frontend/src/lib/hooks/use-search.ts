/**
 * React Query hooks for search operations
 */

import { useMutation, useQuery, UseQueryOptions } from '@tanstack/react-query';
import { MCPError, post } from '../mcp-client';
import type { SearchRequest, SearchResponse } from '../types';

export interface UseSearchParams {
  query?: string;
  queryImageBase64?: string;
  containerIds: string[];
  mode?: 'semantic' | 'hybrid' | 'bm25' | 'crossmodal' | 'graph' | 'hybrid_graph';
  k?: number;
  diagnostics?: boolean;
  graph?: {
    max_hops?: number;
    neighbor_k?: number;
  };
}

/**
 * Search hook using mutation (since search is typically triggered by user action)
 */
export function useSearch() {
  return useMutation<SearchResponse, MCPError, UseSearchParams>({
    mutationFn: async (params) => {
      const request: SearchRequest = {
        query: params.query,
        query_image_base64: params.queryImageBase64,
        container_ids: params.containerIds,
        mode: params.mode || 'hybrid',
        k: params.k || 10,
        diagnostics: params.diagnostics ?? false,
        rerank: false,
        graph: params.graph,
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
  options?: Omit<UseQueryOptions<SearchResponse, MCPError>, 'queryKey' | 'queryFn'>
) {
  return useQuery<SearchResponse, MCPError>({
    queryKey: ['search', params],
    queryFn: async () => {
      if (!params) {
        throw new Error('Search params required');
      }
      const request: SearchRequest = {
        query: params.query,
        query_image_base64: params.queryImageBase64,
        container_ids: params.containerIds,
        mode: params.mode || 'hybrid',
        k: params.k || 10,
        diagnostics: params.diagnostics ?? false,
        rerank: false,
        graph: params.graph,
      };
      const response = await post<SearchResponse>('/v1/search', request);
      return response;
    },
    enabled: !!params && (!!params.query || !!params.queryImageBase64) && params.containerIds.length > 0,
    staleTime: 0, // Search results should always be fresh
    ...options,
  });
}
