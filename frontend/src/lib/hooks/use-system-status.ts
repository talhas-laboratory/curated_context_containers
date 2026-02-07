import { useQuery } from '@tanstack/react-query';

import { get } from '../mcp-client';

export type SystemCheckName = 'postgres' | 'qdrant' | 'minio' | 'neo4j';

export interface SystemStatusResponse {
  version: string;
  request_id: string;
  status: 'ok' | 'degraded';
  required_ok: boolean;
  checks: Record<SystemCheckName, boolean>;
  errors?: Record<string, string>;
  migrations?: unknown;
  issues?: string[];
}

export function useSystemStatus() {
  return useQuery({
    queryKey: ['system-status'],
    queryFn: () => get<SystemStatusResponse>('/v1/system/status'),
    staleTime: 5_000,
    refetchInterval: 10_000,
    retry: false,
  });
}
