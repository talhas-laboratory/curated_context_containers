/**
 * Document management hooks
 */

import { useMutation, useQuery } from '@tanstack/react-query';
import { MCPError, post } from '../mcp-client';
import type {
  DeleteDocumentRequest,
  DeleteDocumentResponse,
  ListDocumentsRequest,
  ListDocumentsResponse,
} from '../types';

export function useContainerDocuments(
  containerId: string | undefined,
  options?: { search?: string; limit?: number; offset?: number }
) {
  return useQuery<ListDocumentsResponse, MCPError>({
    queryKey: ['documents', containerId, options?.search, options?.offset, options?.limit],
    queryFn: async () => {
      if (!containerId) {
        throw new Error('container required');
      }
      const payload: ListDocumentsRequest = {
        container: containerId,
        limit: options?.limit ?? 25,
        offset: options?.offset ?? 0,
        search: options?.search,
      };
      const response = await post<ListDocumentsResponse>('/v1/documents/list', payload);
      return response;
    },
    enabled: !!containerId,
    staleTime: 5 * 1000,
  });
}

export function useDeleteDocument(onSuccess?: () => void, onError?: (error: MCPError) => void) {
  return useMutation<DeleteDocumentResponse, MCPError, DeleteDocumentRequest>({
    mutationFn: async (payload) => {
      const response = await post<DeleteDocumentResponse>('/v1/documents/delete', payload);
      return response;
    },
    onSuccess: () => {
      onSuccess?.();
    },
    onError: (error) => {
      onError?.(error);
    },
  });
}









