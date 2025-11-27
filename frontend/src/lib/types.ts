/**
 * Shared types that mirror server schemas
 */

export interface ContainerSummary {
  id: string;
  name: string;
  theme: string;
  modalities: string[];
  state: 'active' | 'paused' | 'archived';
  stats?: {
    document_count?: number;
    chunk_count?: number;
    size_mb?: number;
    last_ingest?: string;
  };
  created_at?: string;
  updated_at?: string;
}

export interface ContainerDetail extends ContainerSummary {
  description?: string;
  embedder: string;
  embedder_version: string;
  dims: number;
  policy?: Record<string, unknown>;
  manifest_version?: string;
  observability?: {
    diagnostics_enabled?: boolean;
    freshness_lambda?: number;
  };
}

export interface SearchResult {
  chunk_id: string;
  doc_id: string;
  container_id: string;
  container_name?: string;
  title?: string;
  snippet?: string;
  uri?: string;
  score: number;
  stage_scores?: Record<string, number>;
  modality?: 'text' | 'image' | 'pdf';
  provenance?: Record<string, unknown>;
  meta?: Record<string, unknown>;
}

export interface Diagnostics {
  mode?: string;
  containers?: string[];
  bm25_hits?: number;
  vector_hits?: number;
  latency_budget_ms?: number;
  latency_over_budget_ms?: number;
  rerank_applied?: boolean;
  blocked_containers?: string[];
}

export interface JobSummary {
  job_id: string;
  source_uri?: string;
  status: 'queued' | 'running' | 'done' | 'failed';
  submitted_at?: string;
  chunks_created?: number;
  error?: string;
}

export interface ListContainersRequest {
  state?: 'active' | 'paused' | 'archived' | 'all';
  limit?: number;
  offset?: number;
  search?: string;
  include_stats?: boolean;
}

export interface ListContainersResponse {
  containers: ContainerSummary[];
  total: number;
}

export interface DescribeContainerRequest {
  container: string; // UUID or slug
}

export interface DescribeContainerResponse {
  container: ContainerDetail;
  request_id?: string;
  issues?: string[];
}

export interface SearchRequest {
  query: string;
  container_ids: string[];
  mode?: 'semantic' | 'hybrid' | 'bm25';
  rerank?: boolean;
  k?: number;
  diagnostics?: boolean;
}

export interface SearchResponse {
  version: string;
  request_id: string;
  partial?: boolean;
  query: string;
  results: SearchResult[];
  total_hits: number;
  returned: number;
  diagnostics: Diagnostics;
  timings_ms: Record<string, number>;
  issues: string[];
}

export interface ContainerDocument {
  id: string;
  uri?: string;
  title?: string;
  mime: string;
  hash: string;
  state?: string;
  chunk_count: number;
  meta?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ListDocumentsResponse {
  container_id: string;
  documents: ContainerDocument[];
  total: number;
  request_id?: string;
  issues?: string[];
}

export interface DeleteDocumentRequest {
  container: string;
  document_id: string;
}

export interface DeleteDocumentResponse {
  document_id: string;
  deleted: boolean;
  issues?: string[];
}

export interface ListDocumentsRequest {
  container: string;
  limit?: number;
  offset?: number;
  search?: string;
}

export interface AddToContainerRequest {
  container: string; // UUID or slug
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

export interface AddToContainerResponse {
  jobs: JobSummary[];
  request_id?: string;
  issues?: string[];
}
