/**
 * MCP HTTP Client
 * 
 * Handles all communication with the MCP server API, including:
 * - Bearer token authentication
 * - Error handling with typed errors
 * - Request ID passthrough
 */

export interface MCPError {
  code: string;
  status: number;
  message: string;
  issues?: Array<{ code: string; message: string; details?: Record<string, unknown> }>;
}

export interface MCPResponse<T = unknown> {
  version: string;
  request_id?: string;
  partial?: boolean;
  timings_ms?: Record<string, number>;
  issues?: Array<{ code: string; message: string; details?: Record<string, unknown> }>;
  [key: string]: unknown;
}

/**
 * Get MCP base URL from environment or default
 */
function getBaseURL(): string {
  if (typeof window !== 'undefined') {
    return process.env.NEXT_PUBLIC_MCP_BASE_URL || 'http://localhost:7801';
  }
  return process.env.NEXT_PUBLIC_MCP_BASE_URL || 'http://localhost:7801';
}

/**
 * Get bearer token from environment or localStorage
 */
function getToken(): string | null {
  if (typeof window === 'undefined') {
    return process.env.NEXT_PUBLIC_MCP_TOKEN || null;
  }
  
  // Check env first
  if (process.env.NEXT_PUBLIC_MCP_TOKEN) {
    return process.env.NEXT_PUBLIC_MCP_TOKEN;
  }
  
  // Check localStorage
  try {
    const stored = localStorage.getItem('llc_mcp_token');
    if (stored) {
      return stored;
    }
  } catch (e) {
    // localStorage not available (SSR)
  }
  
  return null;
}

/**
 * Set token in localStorage
 */
export function setToken(token: string): void {
  if (typeof window !== 'undefined') {
    try {
      localStorage.setItem('llc_mcp_token', token);
    } catch (e) {
      console.warn('Failed to store token in localStorage', e);
    }
  }
}

/**
 * Get token from storage
 */
export function getStoredToken(): string | null {
  return getToken();
}

/**
 * Remove token from storage
 */
export function clearToken(): void {
  if (typeof window !== 'undefined') {
    try {
      localStorage.removeItem('llc_mcp_token');
    } catch (e) {
      // Ignore
    }
  }
}

/**
 * Fetch JSON from MCP API with bearer token
 */
export async function fetchJson<T = unknown>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T & MCPResponse<T>> {
  const baseURL = getBaseURL();
  const token = getToken();
  
  const url = endpoint.startsWith('http') ? endpoint : `${baseURL}${endpoint}`;
  
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });
    
    // Handle non-2xx responses
    if (!response.ok) {
      let errorData: MCPError;
      
      try {
        const json = await response.json();
        const detail = json.detail;
        const detailMessage = (() => {
          if (!detail) return undefined;
          if (typeof detail === 'string') return detail;
          if (Array.isArray(detail)) {
            return detail
              .map((entry) => entry?.msg || entry?.message || JSON.stringify(entry))
              .join('; ');
          }
          if (typeof detail === 'object') {
            return (detail as { message?: string }).message || JSON.stringify(detail);
          }
          return String(detail);
        })();
        errorData = {
          code: json.error?.code || 'HTTP_ERROR',
          status: response.status,
          message: json.error?.message || json.message || detailMessage || response.statusText,
          issues: json.issues || [],
        };
      } catch (e) {
        errorData = {
          code: 'HTTP_ERROR',
          status: response.status,
          message: response.statusText,
        };
      }
      
      throw errorData;
    }
    
    // Parse JSON response
    const data = await response.json();
    
    // Extract request ID from headers if present
    const requestId = response.headers.get('x-request-id');
    if (requestId && data) {
      data.request_id = requestId;
    }
    
    return data as T & MCPResponse<T>;
  } catch (error) {
    // Re-throw MCPError as-is
    if (error && typeof error === 'object' && 'code' in error) {
      throw error;
    }
    
    // Wrap network errors
    throw {
      code: 'NETWORK_ERROR',
      status: 0,
      message: error instanceof Error ? error.message : 'Network error occurred',
    } as MCPError;
  }
}

/**
 * GET request helper
 */
export async function get<T = unknown>(endpoint: string, options?: RequestInit): Promise<T & MCPResponse<T>> {
  return fetchJson<T>(endpoint, {
    ...options,
    method: 'GET',
  });
}

/**
 * POST request helper
 */
export async function post<T = unknown>(
  endpoint: string,
  body?: unknown,
  options?: RequestInit
): Promise<T & MCPResponse<T>> {
  return fetchJson<T>(endpoint, {
    ...options,
    method: 'POST',
    body: body ? JSON.stringify(body) : undefined,
  });
}

/**
 * DELETE request helper
 */
export async function del<T = unknown>(
  endpoint: string,
  options?: RequestInit
): Promise<T & MCPResponse<T>> {
  return fetchJson<T>(endpoint, {
    ...options,
    method: 'DELETE',
  });
}
