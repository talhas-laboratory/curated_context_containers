/**
 * React Query hooks for adding content to containers
 */

import { useMutation } from '@tanstack/react-query';
import { post } from '../mcp-client';
import type { AddToContainerRequest, AddToContainerResponse } from '../types';

export interface UseAddToContainerParams {
  containerId: string;
  sources: Array<{
    uri?: string;
    file_token?: string;
    title?: string;
    mime?: string;
    modality?: string;
    meta?: Record<string, unknown>;
  }>;
  mode?: 'async' | 'blocking';
  timeout_ms?: number;
}

/**
 * Add content to a container
 */
export function useAddToContainer() {
  return useMutation<AddToContainerResponse, Error, UseAddToContainerParams>({
    mutationFn: async (params) => {
      const request: AddToContainerRequest = {
        container: params.containerId,
        sources: params.sources,
        mode: params.mode || 'async',
        timeout_ms: params.timeout_ms,
      };
      const response = await post<AddToContainerResponse>('/v1/containers/add', request);
      return response;
    },
  });
}

/**
 * Poll job status (optional, for blocking mode or async tracking)
 */
export function useJobs(jobIds: string[]) {
  // Note: This is a placeholder. The actual job status endpoint may not exist in Phase 1
  // For now, jobs are tracked via worker logs or CLI
  // This hook can be implemented when /v1/jobs/status endpoint is available
  return {
    data: null,
    isLoading: false,
    isError: false,
  };
}

