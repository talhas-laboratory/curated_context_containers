/**
 * Admin hooks for refresh/export actions
 */

import { useMutation } from '@tanstack/react-query';

import { MCPError, post } from '../mcp-client';
import type { ExportRequest, ExportResponse, RefreshRequest, RefreshResponse } from '../types';

export function useRefresh(onSuccess?: (response: RefreshResponse) => void, onError?: (error: MCPError) => void) {
  return useMutation<RefreshResponse, MCPError, RefreshRequest>({
    mutationFn: async (payload) => post<RefreshResponse>('/v1/admin/refresh', payload),
    onSuccess,
    onError,
  });
}

export function useExport(onSuccess?: (response: ExportResponse) => void, onError?: (error: MCPError) => void) {
  return useMutation<ExportResponse, MCPError, ExportRequest>({
    mutationFn: async (payload) => post<ExportResponse>('/v1/admin/export', payload),
    onSuccess,
    onError,
  });
}
