import type { Diagnostics, SearchResult } from '../lib/types';

export type SearchResultItem = SearchResult;

export type DiagnosticsPayload = Diagnostics;

export interface TimingBreakdown {
  [stage: string]: number | undefined;
}

export interface GoldenQuerySummary {
  timestamp: string;
  queries: Array<{
    id: string;
    query: string;
    returned: number;
    total_hits: number;
    avg_latency_ms?: number;
  }>;
  sql_checks?: Record<string, {
    chunk_count?: number;
    embedding_cache_rows?: number;
    [key: string]: number | undefined;
  }>;
}
