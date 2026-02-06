/**
 * Shared types that mirror server schemas
 */

export interface ContainerSummary {
  id: string;
  parent_id?: string | null;
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
  graph_hits?: number;
  latency_budget_ms?: number;
  latency_over_budget_ms?: number;
  rerank_applied?: boolean;
  blocked_containers?: string[];
  graph_ms?: number;
}

export interface RefreshRequest {
  container: string;
  strategy?: 'in_place' | 'shadow';
  embedder_version?: string | null;
  graph_llm_enabled?: boolean;
}

export interface RefreshResponse {
  version: string;
  request_id: string;
  partial?: boolean;
  job_id: string;
  status: string;
  timings_ms?: Record<string, number>;
  issues?: string[];
}

export interface ExportRequest {
  container: string;
  format?: 'tar' | 'zip';
  include_vectors?: boolean;
  include_blobs?: boolean;
}

export interface ExportResponse {
  version: string;
  request_id: string;
  partial?: boolean;
  job_id: string;
  status: string;
  timings_ms?: Record<string, number>;
  issues?: string[];
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
  parent_id?: string;
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

export interface CreateContainerRequest {
  name: string;
  theme: string;
  parent_id?: string;
  description?: string;
  modalities?: string[];
  embedder?: string;
  embedder_version?: string;
  dims?: number;
  policy?: Record<string, unknown>;
  mission_context?: string;
  visibility?: 'private' | 'team' | 'public';
  collaboration_policy?: 'read-only' | 'contribute';
  auto_refresh?: boolean;
}

export interface DeleteContainerRequest {
  container: string; // UUID or slug
  permanent?: boolean;
}

export interface ContainerLifecycleResponse {
  version: string;
  request_id: string;
  success: boolean;
  container_id?: string;
  message?: string;
  timings_ms?: Record<string, number>;
  issues?: string[];
}

export interface SearchRequest {
  query?: string;
  query_image_base64?: string;
  container_ids: string[];
  mode?: 'semantic' | 'hybrid' | 'bm25' | 'crossmodal' | 'graph' | 'hybrid_graph';
  rerank?: boolean;
  k?: number;
  diagnostics?: boolean;
  graph?: {
    max_hops?: number;
    neighbor_k?: number;
  };
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
  graph_context?: {
    nodes?: Array<Record<string, unknown>>;
    edges?: Array<Record<string, unknown>>;
    snippets?: Array<Record<string, unknown>>;
  };
}

export interface GraphNode {
  id: string;
  label?: string | null;
  type?: string | null;
  summary?: string | null;
  properties?: Record<string, unknown>;
  source_chunk_ids?: string[];
  score?: number | null;
}

export interface GraphEdge {
  source: string;
  target: string;
  type?: string | null;
  properties?: Record<string, unknown>;
  source_chunk_ids?: string[];
  score?: number | null;
}

export interface GraphSnippet {
  chunk_id: string;
  doc_id: string;
  uri?: string | null;
  title?: string | null;
  text?: string | null;
}

export interface GraphSearchResponse {
  version: string;
  request_id: string;
  partial?: boolean;
  nodes: GraphNode[];
  edges: GraphEdge[];
  snippets: GraphSnippet[];
  diagnostics?: Diagnostics;
  timings_ms?: Record<string, number>;
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
