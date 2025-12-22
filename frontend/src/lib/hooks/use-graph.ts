import { useQuery } from '@tanstack/react-query';
import { MCPError, get, post } from '../mcp-client';
import type { GraphSearchResponse } from '../types';

export interface GraphSearchParams {
  containerId: string;
  query: string;
  mode?: 'nl' | 'cypher';
  maxHops?: number;
  k?: number;
  diagnostics?: boolean;
}

export function useGraphSearch(params: GraphSearchParams | null) {
  return useQuery<GraphSearchResponse, MCPError>({
    queryKey: ['graph-search', params],
    queryFn: async () => {
      if (!params) throw new Error('Graph search params required');
      const payload = {
        container: params.containerId,
        query: params.query,
        mode: params.mode || 'nl',
        max_hops: params.maxHops ?? 2,
        k: params.k ?? 20,
        diagnostics: params.diagnostics ?? true,
      };
      return post<GraphSearchResponse>('/v1/containers/graph_search', payload);
    },
    enabled: !!params && !!params.query && !!params.containerId,
    staleTime: 0,
    retry: 1,
  });
}

export function useGraphSchema(containerId: string | null) {
  return useQuery<any, MCPError>({
    queryKey: ['graph-schema', containerId],
    queryFn: async () => {
      if (!containerId) throw new Error('Container id required');
      return get<any>(`/v1/containers/graph_schema?container=${encodeURIComponent(containerId)}`);
    },
    enabled: !!containerId,
    staleTime: 5 * 60 * 1000,
  });
}
