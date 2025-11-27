/**
 * React Query hooks for job status polling
 */

import { useQuery } from '@tanstack/react-query';
import { post } from '../mcp-client';

export interface JobStatus {
  job_id: string;
  status: 'queued' | 'running' | 'done' | 'failed' | 'not_found';
  error?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface JobStatusResponse {
  jobs: JobStatus[];
}

/**
 * Poll job status for one or more job IDs
 */
export function useJobStatus(jobIds: string[], enabled: boolean = true) {
  return useQuery<JobStatusResponse>({
    queryKey: ['jobs', 'status', jobIds.sort().join(',')],
    queryFn: async () => {
      const response = await post<JobStatusResponse>('/v1/jobs/status', { job_ids: jobIds });
      return response;
    },
    enabled: enabled && jobIds.length > 0,
    refetchInterval: (query) => {
      // Poll every 2 seconds if any job is still in progress
      const data = query.state.data;
      if (data?.jobs) {
        const inProgress = data.jobs.some(
          (job) => job.status === 'queued' || job.status === 'running'
        );
        return inProgress ? 2000 : false;
      }
      return 2000;
    },
    staleTime: 0, // Always refetch
  });
}

