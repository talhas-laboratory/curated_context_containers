/**
 * React Query hooks for container operations
 */

import { useMutation, useQuery, useQueryClient, UseMutationOptions, UseQueryOptions } from '@tanstack/react-query';
import { MCPError, del, post } from '../mcp-client';
import type {
  ListContainersRequest,
  ListContainersResponse,
  DescribeContainerRequest,
  DescribeContainerResponse,
  CreateContainerRequest,
  DeleteContainerRequest,
  ContainerLifecycleResponse,
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
 * Create a new container
 */
export function useCreateContainer(
  options?: Omit<
    UseMutationOptions<ContainerLifecycleResponse, MCPError, CreateContainerRequest>,
    'mutationFn'
  >
) {
  const queryClient = useQueryClient();
  const { onSuccess, ...restOptions } = options || {};

  return useMutation<ContainerLifecycleResponse, MCPError, CreateContainerRequest>({
    mutationFn: async (payload) => {
      const response = await post<ContainerLifecycleResponse>('/v1/containers/create', payload);
      return response;
    },
    onSuccess: (data, variables, context) => {
      queryClient.invalidateQueries({ queryKey: ['containers'] });
      onSuccess?.(data, variables, context, undefined);
    },
    ...restOptions,
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

/**
 * Delete (archive or permanently delete) a container
 */
export function useDeleteContainer(
  options?: Omit<
    UseMutationOptions<ContainerLifecycleResponse, MCPError, DeleteContainerRequest>,
    'mutationFn'
  >
) {
  const queryClient = useQueryClient();
  const { onSuccess, ...restOptions } = options || {};

  return useMutation<ContainerLifecycleResponse, MCPError, DeleteContainerRequest>({
    mutationFn: async ({ container, permanent }) => {
      const query = permanent ? '?permanent=true' : '';
      const response = await del<ContainerLifecycleResponse>(`/v1/containers/${container}${query}`);
      return response;
    },
    onSuccess: (data, variables, context) => {
      queryClient.invalidateQueries({ queryKey: ['containers'] });
      if (variables?.container) {
        queryClient.invalidateQueries({ queryKey: ['containers', 'describe', variables.container] });
      }
      onSuccess?.(data, variables, context, undefined);
    },
    ...restOptions,
  });
}
