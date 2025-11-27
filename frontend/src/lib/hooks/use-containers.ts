/**
 * React Query hooks for container operations
 */

import { useQuery, UseQueryOptions } from '@tanstack/react-query';
import { get, post } from '../mcp-client';
import type {
  ListContainersRequest,
  ListContainersResponse,
  DescribeContainerRequest,
  DescribeContainerResponse,
} from '../types';

/**
 * List containers with optional state filter
 */
export function useListContainers(
  state?: 'active' | 'paused' | 'archived' | 'all',
  options?: Omit<UseQueryOptions<ListContainersResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery<ListContainersResponse>({
    queryKey: ['containers', 'list', state || 'active'],
    queryFn: async () => {
      const request: ListContainersRequest = {
        state: state || 'active',
        limit: 100,
        offset: 0,
      };
      const response = await post<ListContainersResponse>('/v1/containers/list', request);
      return response;
    },
    staleTime: 30 * 1000, // 30 seconds
    ...options,
  });
}

/**
 * Describe a single container by ID or slug
 */
export function useDescribeContainer(
  idOrSlug: string,
  options?: Omit<UseQueryOptions<DescribeContainerResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery<DescribeContainerResponse>({
    queryKey: ['containers', 'describe', idOrSlug],
    queryFn: async () => {
      const request: DescribeContainerRequest = {
        container: idOrSlug,
      };
      const response = await post<DescribeContainerResponse>('/v1/containers/describe', request);
      return response;
    },
    enabled: !!idOrSlug,
    staleTime: 30 * 1000,
    ...options,
  });
}
