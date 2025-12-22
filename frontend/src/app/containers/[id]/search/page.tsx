'use client';

import { useEffect, useRef, useState, type FormEvent } from 'react';
import { useParams } from 'next/navigation';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';

import { GlassShell } from '../../../../components/glass/GlassShell';
import { GlassCard } from '../../../../components/glass/GlassCard';
import { GlassInput } from '../../../../components/glass/GlassInput';
import { ResultItem } from '../../../../components/ResultItem';
import { DiagnosticsRail } from '../../../../components/DiagnosticsRail';
import { DocumentModal } from '../../../../components/DocumentModal';
import { ContainerDocumentsPanel } from '../../../../components/ContainerDocumentsPanel';
import { MultiContainerSelector } from '../../../../components/MultiContainerSelector';
import { AdminActionModal } from '../../../../components/AdminActionModal';
import { GraphModeToggle } from '../../../../components/GraphModeToggle';
import { GraphDiagnosticsBar } from '../../../../components/GraphDiagnosticsBar';
import { GraphResultsTable } from '../../../../components/GraphResultsTable';
import { GraphQueryPanel } from '../../../../components/GraphQueryPanel';
import { useDescribeContainer } from '../../../../lib/hooks/use-containers';
import { useListContainers } from '../../../../lib/hooks/use-containers';
import { useSearch } from '../../../../lib/hooks/use-search';
import { useRefresh, useExport } from '../../../../lib/hooks/use-admin';
import { useGraphSearch, type GraphSearchParams } from '../../../../lib/hooks/use-graph';
import { useJobStatus } from '../../../../lib/hooks/use-job-status';
import type { SearchResult } from '../../../../lib/types';
import { useKeyboardShortcuts } from '../../../../lib/keyboard';

const MODES: Array<{ label: string; value: 'semantic' | 'hybrid' | 'bm25' | 'crossmodal' | 'graph' | 'hybrid_graph' }> = [
  { label: 'Hybrid', value: 'hybrid' },
  { label: 'Semantic', value: 'semantic' },
  { label: 'BM25', value: 'bm25' },
  { label: 'Crossmodal', value: 'crossmodal' },
  { label: 'Graph', value: 'graph' },
  { label: 'Hybrid Graph', value: 'hybrid_graph' },
];

export default function ContainerSearchPage() {
  const params = useParams<{ id: string }>();
  const containerId = params?.id;
  const searchInputRef = useRef<HTMLInputElement>(null);

  const [query, setQuery] = useState('');
  const [mode, setMode] = useState<'semantic' | 'hybrid' | 'bm25' | 'crossmodal' | 'graph' | 'hybrid_graph'>('hybrid');
  const [k, setK] = useState(10);
  const [diagnosticsEnabled, setDiagnosticsEnabled] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [activeResult, setActiveResult] = useState<SearchResult | null>(null);
  const [selectedContainers, setSelectedContainers] = useState<string[]>(containerId ? [containerId] : []);
  const [targetContainer, setTargetContainer] = useState<string>(containerId || '');
  const [refreshModalOpen, setRefreshModalOpen] = useState(false);
  const [exportModalOpen, setExportModalOpen] = useState(false);
  const [refreshStrategy, setRefreshStrategy] = useState<'in_place' | 'shadow'>('in_place');
  const [embedderVersion, setEmbedderVersion] = useState('');
  const [exportFormat, setExportFormat] = useState<'tar' | 'zip'>('tar');
  const [includeVectors, setIncludeVectors] = useState(true);
  const [includeBlobs, setIncludeBlobs] = useState(true);
  const [useLlmExtractor, setUseLlmExtractor] = useState(false);
  const [adminError, setAdminError] = useState<string | null>(null);
  const [adminJobs, setAdminJobs] = useState<Array<{ id: string; kind: 'refresh' | 'export'; container: string }>>([]);
  const [queryImage, setQueryImage] = useState<string | null>(null);
  const [maxHops, setMaxHops] = useState<number>(2);
  const [rawCypherEnabled, setRawCypherEnabled] = useState<boolean>(false);
  const [rawCypher, setRawCypher] = useState<string>('');
  const [graphSearchParams, setGraphSearchParams] = useState<GraphSearchParams | null>(null);
  const prefersReducedMotion = useReducedMotion();

  const addAdminJob = (jobId: string, kind: 'refresh' | 'export', container: string) => {
    setAdminJobs((prev) => {
      if (prev.some((job) => job.id === jobId)) return prev;
      return [...prev, { id: jobId, kind, container }];
    });
  };

  const normalizeContainerId = (value: string) => {
    const match = availableContainers.find((c) => c.id === value || c.name === value);
    return match ? match.id : value;
  };

  const {
    data: containerDetail,
    isLoading: containerLoading,
    error: containerError,
  } = useDescribeContainer(containerId || '');
  const { data: allContainers, isLoading: loadingContainers, error: containersError } = useListContainers('active');
  const { mutate: runSearch, data: searchData, isPending: searching, error: searchError } = useSearch();
  const {
    data: graphSearchData,
    isFetching: graphSearching,
    error: graphSearchError,
  } = useGraphSearch(graphSearchParams);
  const availableContainers = allContainers?.containers || [];

  const { data: jobStatusData, isLoading: jobStatusLoading } = useJobStatus(
    adminJobs.map((job) => job.id),
    adminJobs.length > 0
  );

  const refreshMutation = useRefresh(
    (response) => {
      if (!response?.job_id) return;
      setAdminError(null);
      setRefreshModalOpen(false);
      addAdminJob(response.job_id, 'refresh', targetContainer || containerId || '');
    },
    (error) => setAdminError(error.message)
  );

  const exportMutation = useExport(
    (response) => {
      if (!response?.job_id) return;
      setAdminError(null);
      setExportModalOpen(false);
      addAdminJob(response.job_id, 'export', targetContainer || containerId || '');
    },
    (error) => setAdminError(error.message)
  );

  const results = graphSearchParams ? [] : searchData?.results || [];
  const graphContext = graphSearchParams
    ? {
        nodes: graphSearchData?.nodes || [],
        edges: graphSearchData?.edges || [],
        snippets: graphSearchData?.snippets || [],
      }
    : searchData?.graph_context;
  const diagnostics = graphSearchParams ? graphSearchData?.diagnostics : searchData?.diagnostics;
  const timings = graphSearchParams ? graphSearchData?.timings_ms : searchData?.timings_ms;
  const issues = graphSearchParams ? graphSearchData?.issues || [] : searchData?.issues || [];
  const jobStatuses = jobStatusData?.jobs ?? [];
  const graphNodes = (graphContext?.nodes as any[]) || [];
  const graphEdges = (graphContext?.edges as any[]) || [];
  const graphSnippets = (graphContext?.snippets as any[]) || [];
  const hasGraphContext = graphNodes.length > 0 || graphEdges.length > 0 || graphSnippets.length > 0;
  const graphHits =
    diagnostics && typeof (diagnostics as any)?.graph_hits === 'number'
      ? (diagnostics as any).graph_hits
      : hasGraphContext
        ? graphNodes.length
        : undefined;
  const graphMs = timings?.graph_ms;
  const showGraphSection = hasGraphContext || graphMs !== undefined || graphHits !== undefined;

  const getContainerLabel = (id: string) => {
    return availableContainers.find((c) => c.id === id)?.name || id;
  };

  const resolveJobStatus = (jobId: string) => jobStatuses.find((job) => job.job_id === jobId);

  const getStatusLabel = (status?: string) => {
    switch (status) {
      case 'queued':
        return 'Queued';
      case 'running':
        return 'Running';
      case 'done':
        return 'Completed';
      case 'failed':
        return 'Failed';
      case 'not_found':
        return 'Not found';
      default:
        return 'Unknown';
    }
  };

  const getStatusTone = (status?: string) => {
    switch (status) {
      case 'done':
        return 'text-emerald-700 bg-emerald-50 border-emerald-200';
      case 'running':
        return 'text-blue-700 bg-blue-50 border-blue-200';
      case 'queued':
        return 'text-slate-700 bg-slate-50 border-slate-200';
      case 'failed':
        return 'text-ember bg-ember/5 border-ember/40';
      case 'not_found':
        return 'text-ink-2 bg-paper-0 border-line-2';
      default:
        return 'text-ink-2 bg-paper-0 border-line-2';
    }
  };

  useEffect(() => {
    setSelectedIndex(0);
  }, [searchData]);

  useEffect(() => {
    if (containerId) {
      const normalized = normalizeContainerId(containerId);
      if (!selectedContainers.includes(normalized)) {
        setSelectedContainers((prev) => [normalized, ...prev.filter((id) => id !== containerId)]);
      }
    }
  }, [containerId, availableContainers]);

  useEffect(() => {
    if (containerDetail?.container.id) {
      setTargetContainer(containerDetail.container.id);
    } else if (containerId) {
      setTargetContainer(normalizeContainerId(containerId));
    }
  }, [containerId, containerDetail?.container.id, availableContainers]);

  useEffect(() => {
    if (mode !== 'graph') {
      setRawCypherEnabled(false);
      setGraphSearchParams(null);
      setRawCypher('');
    }
  }, [mode]);

  useEffect(() => {
    if (!targetContainer && availableContainers.length > 0) {
      setTargetContainer(availableContainers[0].id);
    }
  }, [availableContainers, targetContainer]);

  useEffect(() => {
    const cleanup = useKeyboardShortcuts({
      '/': () => {
        searchInputRef.current?.focus();
      },
      arrowdown: () => {
        if (!results.length || activeResult) return;
        setSelectedIndex((prev) => Math.min(prev + 1, results.length - 1));
      },
      arrowup: () => {
        if (!results.length || activeResult) return;
        setSelectedIndex((prev) => Math.max(prev - 1, 0));
      },
      enter: () => {
        if (activeResult || !results.length) return;
        setActiveResult(results[selectedIndex]);
      },
    });
    return () => {
      cleanup?.();
    };
  }, [results, activeResult, selectedIndex]);

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    console.log('handleSubmit called', { query, containerId, mode, k });
    const containerTarget = targetContainer || selectedContainers[0];
    if (mode === 'graph' && rawCypherEnabled && rawCypher.trim()) {
      if (!containerTarget) {
        console.warn('Graph search blocked: choose a container for Cypher query');
        return;
      }
      setGraphSearchParams({
        containerId: containerTarget,
        query: rawCypher.trim(),
        mode: 'cypher',
        maxHops,
        diagnostics: diagnosticsEnabled,
      });
      setActiveResult(null);
      return;
    }
    if ((!query && !queryImage) || selectedContainers.length === 0) {
      console.warn('Search blocked: missing query or container selection', { query, queryImage, selectedContainers });
      return;
    }
    if ((mode === 'graph' || mode === 'hybrid_graph') && queryImage) {
      console.warn('Graph modes require text query only');
      return;
    }
    setGraphSearchParams(null);
    console.log('Running search...');
    const normalizedContainers = selectedContainers.map((id) => normalizeContainerId(id));
    runSearch({
      query: queryImage ? undefined : query,
      queryImageBase64: queryImage || undefined,
      containerIds: normalizedContainers,
      mode: queryImage ? 'crossmodal' : mode,
      k,
      diagnostics: diagnosticsEnabled,
      graph: mode === 'graph' || mode === 'hybrid_graph' ? { max_hops: maxHops } : undefined,
    });
  };

  const handleRefreshSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!targetContainer) {
      setAdminError('Choose a container to refresh.');
      return;
    }
    setAdminError(null);
    refreshMutation.mutate({
      container: targetContainer,
      strategy: refreshStrategy,
      embedder_version: embedderVersion.trim() || undefined,
      graph_llm_enabled: useLlmExtractor,
    });
  };

  const handleExportSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!targetContainer) {
      setAdminError('Choose a container to export.');
      return;
    }
    setAdminError(null);
    exportMutation.mutate({
      container: targetContainer,
      format: exportFormat,
      include_vectors: includeVectors,
      include_blobs: includeBlobs,
    });
  };

  const handleRemoveJob = (jobId: string) => {
    setAdminJobs((prev) => prev.filter((job) => job.id !== jobId));
  };

  const activeSearchError = graphSearchParams ? graphSearchError : searchError;
  const isLoading = graphSearchParams ? graphSearching : searching;
  const hasData = graphSearchParams ? !!graphSearchData : !!searchData;
  const showEmptyState =
    !isLoading &&
    hasData &&
    results.length === 0 &&
    !((graphContext?.nodes && graphContext.nodes.length) || (graphContext?.edges && graphContext.edges.length));
  const showInitialState = !isLoading && !hasData && !activeSearchError;
  const stats = containerDetail?.container.stats;

  const sidebarContent = (
    <div className="space-y-8">
      <GlassCard className="space-y-4">
        <h2 className="font-serif text-xl italic text-ink-1">
          {containerLoading ? 'Loading…' : containerDetail?.container.name || '—'}
        </h2>
        <p className="text-sm text-ink-2 font-light">
          {containerError ? 'Error loading container' : containerDetail?.container.theme}
        </p>
        
        <div className="pt-4 space-y-3 border-t border-line-1/50">
          <div className="flex items-center justify-between text-sm">
            <span className="text-ink-2">Documents</span>
            <span className="text-ink-1 font-mono">{stats?.document_count ?? '—'}</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-ink-2">Chunks</span>
            <span className="text-ink-1 font-mono">{stats?.chunk_count ?? '—'}</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-ink-2">Last ingest</span>
            <span className="text-ink-1 font-mono text-xs">
              {stats?.last_ingest ? new Date(stats.last_ingest).toLocaleDateString() : '—'}
            </span>
          </div>
        </div>
      </GlassCard>

      <ContainerDocumentsPanel containerId={containerId} />

      <GlassCard className="space-y-4" data-testid="admin-actions">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.08em] text-ink-2">Maintenance</p>
            <h3 className="text-lg font-serif text-ink-1">Refresh &amp; Export</h3>
            <p className="text-sm text-ink-2">Keep embeddings current or take a snapshot.</p>
          </div>
          <span className="rounded-full border border-line-2 px-2 py-1 text-[10px] uppercase tracking-[0.08em] text-ink-2">Phase 2</span>
        </div>

        <div className="grid gap-2">
          <button
            type="button"
            onClick={() => {
              setAdminError(null);
              setRefreshModalOpen(true);
            }}
            disabled={loadingContainers || availableContainers.length === 0}
            className="rounded-full border border-ink-1 bg-white px-4 py-2 text-sm font-medium text-ink-1 transition hover:bg-white/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink-1/30 disabled:cursor-not-allowed disabled:opacity-60"
          >
            Refresh embeddings
          </button>
          <button
            type="button"
            onClick={() => {
              setAdminError(null);
              setExportModalOpen(true);
            }}
            disabled={loadingContainers || availableContainers.length === 0}
            className="rounded-full border border-line-2 px-4 py-2 text-sm text-ink-1 transition hover:border-ink-1 hover:text-ink-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink-1/20 disabled:cursor-not-allowed disabled:opacity-60"
          >
            Export container
          </button>
        </div>

        {adminError && <p className="text-xs text-ember" role="alert">{adminError}</p>}

        {adminJobs.length > 0 && (
          <div className="space-y-2" data-testid="admin-jobs">
            {adminJobs.map((job) => {
              const statusEntry = resolveJobStatus(job.id);
              const status = statusEntry?.status;
              const error = statusEntry?.error;
              return (
                <div
                  key={job.id}
                  className={`flex items-start justify-between gap-3 rounded-xl border px-3 py-2 ${getStatusTone(status)}`}
                >
                  <div className="space-y-1">
                    <p className="text-sm font-medium text-ink-1">
                      {job.kind === 'refresh' ? 'Refresh' : 'Export'} · {getContainerLabel(job.container)}
                    </p>
                    <p className="text-xs text-ink-2">
                      Status: {getStatusLabel(status)}
                      {jobStatusLoading && ' …'}
                    </p>
                    {error && <p className="text-xs text-ember">{error}</p>}
                  </div>
                  <div className="flex flex-col items-end gap-2 text-[10px] font-mono text-ink-2">
                    <span>{job.id.slice(0, 8)}</span>
                    <button
                      type="button"
                      onClick={() => handleRemoveJob(job.id)}
                      className="rounded-full border border-line-2 px-2 py-1 text-[10px] uppercase tracking-[0.08em] text-ink-2 transition hover:border-ink-1 hover:text-ink-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink-1/20"
                    >
                      Dismiss
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {adminJobs.length === 0 && !loadingContainers && (
          <p className="text-xs text-ink-2">No maintenance jobs yet.</p>
        )}
      </GlassCard>

      {diagnosticsEnabled && (
        <DiagnosticsRail
          visible={true}
          diagnostics={diagnostics}
          timings={timings || null}
          goldenSummary={null}
        />
      )}
    </div>
  );

  return (
    <GlassShell
      sidebar={sidebarContent}
      headline="Search Workspace"
      description="Ask within a single container."
    >
      <div className="space-y-8 pb-24">
        {/* Search Input Area */}
        <div className="relative max-w-3xl mx-auto w-full z-20">
          <form onSubmit={handleSubmit}>
             <GlassInput
               ref={searchInputRef}
               value={query}
               onChange={(e) => setQuery(e.target.value)}
               onKeyDown={(e) => {
                 if (e.key === 'Enter') {
                   e.preventDefault();
                   handleSubmit();
                 }
               }}
               placeholder={
                 mode === 'crossmodal'
                   ? 'Paste optional description for your image query…'
                   : `Search ${containerDetail?.container.name ?? 'container'}…`
               }
               className="w-full text-lg"
               data-testid="search-input"
               icon={
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="11" cy="11" r="8"></circle>
                  <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                </svg>
               }
             />
             <button type="submit" data-testid="search-submit" className="sr-only">
               Search
             </button>
          </form>
        </div>

        <div className="flex flex-col lg:flex-row gap-8">
           <div className="flex-1 space-y-6">
              {/* Controls */}
              <div className="flex flex-wrap items-center justify-between gap-4 px-2">
                <GraphModeToggle options={MODES} value={mode} onChange={(val) => setMode(val as typeof mode)} />

                <div className="flex items-center gap-4">
                   <MultiContainerSelector
                     containers={allContainers?.containers || []}
                     selectedIds={selectedContainers}
                     onChange={setSelectedContainers}
                     busy={loadingContainers}
                     error={containersError ? 'Failed to load containers' : null}
                   />
                   <div className="flex items-center gap-2 text-sm text-ink-2">
                     <input
                       type="file"
                       accept="image/*"
                       id="image-query"
                       className="hidden"
                       onChange={async (e) => {
                         const file = e.target.files?.[0];
                         if (!file) return;
                         const buf = await file.arrayBuffer();
                         const base64 = btoa(String.fromCharCode(...new Uint8Array(buf)));
                         setQueryImage(base64);
                         setMode('crossmodal');
                       }}
                     />
                     <label
                       htmlFor="image-query"
                       className="cursor-pointer rounded-full border border-line-2 px-3 py-1.5 bg-white/60 hover:border-ink-1 hover:text-ink-1 transition"
                     >
                       {queryImage ? 'Replace image query' : 'Add image query'}
                     </label>
                     {queryImage && (
                       <button
                         type="button"
                         onClick={() => setQueryImage(null)}
                         className="rounded-full border border-line-2 px-2 py-1 text-xs uppercase tracking-[0.08em] text-ink-2 hover:border-ink-1 hover:text-ink-1 transition"
                       >
                         Clear
                       </button>
                     )}
                   </div>
                   <label className="flex items-center gap-2 text-sm text-ink-2 cursor-pointer select-none">
                     <input 
                       type="checkbox" 
                       checked={diagnosticsEnabled} 
                       onChange={(e) => setDiagnosticsEnabled(e.target.checked)}
                       className="rounded border-ink-2/30 text-ink-1 focus:ring-ink-1/20"
                     />
                     Diagnostics
                   </label>
                   
                  <div className="flex items-center gap-2 text-sm text-ink-2 bg-white/40 rounded-full px-3 py-1 border border-white/30">
                    <span>k=</span>
                    <select
                      value={k}
                      onChange={(e) => setK(Number(e.target.value))}
                      className="bg-transparent border-none p-0 focus:ring-0 text-ink-1 font-mono cursor-pointer"
                    >
                      {[5, 10, 20, 30, 40, 50].map((n) => (
                        <option key={n} value={n}>{n}</option>
                      ))}
                    </select>
                  </div>
                  {(mode === 'graph' || mode === 'hybrid_graph') && (
                    <div className="flex items-center gap-2 text-sm text-ink-2 bg-white/40 rounded-full px-3 py-1 border border-white/30">
                      <span>hops</span>
                      <select
                        value={maxHops}
                        onChange={(e) => setMaxHops(Number(e.target.value))}
                        className="bg-transparent border-none p-0 focus:ring-0 text-ink-1 font-mono cursor-pointer"
                      >
                        {[1, 2, 3].map((n) => (
                          <option key={n} value={n}>{n}</option>
                        ))}
                      </select>
                    </div>
                  )}
                </div>
              </div>
              <GraphQueryPanel
                mode={mode}
                rawCypherEnabled={rawCypherEnabled}
                rawCypher={rawCypher}
                onToggleRawCypher={(enabled) => {
                  setRawCypherEnabled(enabled);
                  if (!enabled) {
                    setRawCypher('');
                    setGraphSearchParams(null);
                  }
                }}
                onChangeRawCypher={(val) => setRawCypher(val)}
                onSubmit={() => handleSubmit()}
              />

              {/* Issues & Errors */}
              {(issues.length > 0 || activeSearchError) && (
                <motion.div 
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="bg-red-50/50 border border-red-100 rounded-xl p-4 text-sm"
                  data-testid="search-error"
                >
                  {issues.length > 0 && (
                    <div className="flex flex-wrap gap-2 mb-2">
                      {issues.map((issue) => (
                        <span key={issue} className="px-2 py-1 bg-white/60 rounded-md text-red-600 border border-red-200 text-xs font-mono">
                          {issue}
                        </span>
                      ))}
                    </div>
                  )}
                  {activeSearchError && (
                    <p className="text-red-600">{(activeSearchError as Error).message || 'Search error'}</p>
                  )}
                </motion.div>
              )}

              {/* Results List */}
              <div className="space-y-4 min-h-[200px]">
                {isLoading && (
                  <div className="text-center py-12 text-ink-2">
                     <div className="w-8 h-8 border-2 border-ink-2/30 border-t-ink-2 rounded-full animate-spin mx-auto mb-3"/>
                     <p className="animate-pulse">Retrieving chunks...</p>
                  </div>
                )}
                
                {showInitialState && (
                  <div className="text-center py-20 text-ink-2/50 font-serif italic text-xl">
                    "The latent space awaits your query."
                  </div>
                )}

                {showEmptyState && (
                  <div className="text-center py-12 bg-white/30 rounded-2xl border border-white/40" data-testid="search-status">
                    <p className="text-ink-1 font-medium">No hits</p>
                    <p className="text-ink-2 text-sm mt-1">Try adjusting your query or increasing k.</p>
                  </div>
                )}

                <AnimatePresence mode="popLayout">
                  {results.map((result, idx) => (
                    <motion.div
                      key={result.chunk_id}
                      initial={prefersReducedMotion ? false : { opacity: 0, y: 20 }}
                      animate={prefersReducedMotion ? { opacity: 1 } : { opacity: 1, y: 0 }}
                      exit={prefersReducedMotion ? { opacity: 0 } : { opacity: 0, scale: 0.95 }}
                      transition={prefersReducedMotion ? { duration: 0 } : { delay: idx * 0.05 }}
                    >
                      <ResultItem
                        result={result}
                        diagnosticsVisible={diagnosticsEnabled}
                        selected={idx === selectedIndex}
                        onSelect={(res) => {
                          setActiveResult(res);
                          setSelectedIndex(idx);
                        }}
                      />
                    </motion.div>
                  ))}
                </AnimatePresence>

                {showGraphSection ? (
                  <div className="space-y-3">
                    <GraphDiagnosticsBar
                      graphMs={graphMs}
                      graphHits={graphHits}
                      modeLabel={graphSearchParams ? (graphSearchParams.mode === 'cypher' ? 'cypher' : 'nl') : mode}
                      issues={issues}
                    />
                    <GraphResultsTable nodes={graphNodes} edges={graphEdges} snippets={graphSnippets} maxHops={maxHops} />
                  </div>
                ) : null}
              </div>
           </div>
        </div>
      </div>

      <DocumentModal result={activeResult} isOpen={!!activeResult} onClose={() => setActiveResult(null)} />
      <AdminActionModal
        open={refreshModalOpen}
        title="Refresh embeddings"
        description="Re-embed this container with the current or new embedder version."
        onClose={() => setRefreshModalOpen(false)}
        onSubmit={handleRefreshSubmit}
        submitLabel={refreshMutation.isPending ? 'Running…' : 'Trigger refresh'}
        busy={refreshMutation.isPending}
        error={adminError}
      >
        <label className="block space-y-1">
          <span className="text-[11px] uppercase tracking-[0.08em] text-ink-2">Container</span>
          <select
            value={targetContainer}
            onChange={(e) => setTargetContainer(e.target.value)}
            className="w-full rounded-lg border border-line-2 bg-white px-3 py-2 text-sm text-ink-1 focus:border-ink-1 focus:outline-none focus:ring-1 focus:ring-ink-1/30"
            disabled={availableContainers.length === 0}
            data-testid="admin-container-select"
          >
            {availableContainers.length === 0 && <option value="">No containers</option>}
            {availableContainers.map((container) => (
              <option key={container.id} value={container.id}>
                {container.name}
              </option>
            ))}
          </select>
        </label>

        <div className="grid grid-cols-2 gap-2" role="group" aria-label="Refresh strategy">
          {(
            [
              { value: 'in_place', label: 'In-place', hint: 'Re-embed and keep collection id' },
              { value: 'shadow', label: 'Shadow', hint: 'Build parallel copy, then swap' },
            ] as const
          ).map((option) => (
            <label
              key={option.value}
              className={`block cursor-pointer rounded-xl border px-3 py-2 text-sm transition focus-within:ring-2 focus-within:ring-ink-1/30 ${
                refreshStrategy === option.value ? 'border-ink-1 bg-white' : 'border-line-2 bg-white/70'
              }`}
            >
              <div className="flex items-center gap-2">
                <input
                  type="radio"
                  name="refresh-strategy"
                  value={option.value}
                  checked={refreshStrategy === option.value}
                  onChange={() => setRefreshStrategy(option.value)}
                  className="h-4 w-4 text-ink-1 focus:ring-ink-1/30"
                />
                <div>
                  <p className="font-medium text-ink-1">{option.label}</p>
                  <p className="text-xs text-ink-2">{option.hint}</p>
                </div>
              </div>
            </label>
          ))}
        </div>

        <label className="block space-y-1">
          <span className="text-[11px] uppercase tracking-[0.08em] text-ink-2">Embedder version (optional)</span>
          <input
            type="text"
            value={embedderVersion}
            onChange={(e) => setEmbedderVersion(e.target.value)}
            placeholder="e.g., 1.1.0"
            className="w-full rounded-lg border border-line-2 bg-white px-3 py-2 text-sm text-ink-1 focus:border-ink-1 focus:outline-none focus:ring-1 focus:ring-ink-1/30"
          />
          <p className="text-xs text-ink-2">Leave blank to reuse the current embedder version.</p>
        </label>
        <label className="flex items-center gap-2 text-sm text-ink-1">
          <input
            type="checkbox"
            checked={useLlmExtractor}
            onChange={(e) => setUseLlmExtractor(e.target.checked)}
            className="h-4 w-4 rounded border-ink-2/40 text-ink-1 focus:ring-ink-1/30"
          />
          Use LLM-assisted graph extraction (OpenRouter)
        </label>
        <p className="text-xs text-ink-2 -mt-1">
          Applies during refresh ingest; falls back to heuristics if unavailable.
        </p>
      </AdminActionModal>

      <AdminActionModal
        open={exportModalOpen}
        title="Export container"
        description="Create a tar or zip snapshot with metadata, vectors, and blobs."
        onClose={() => setExportModalOpen(false)}
        onSubmit={handleExportSubmit}
        submitLabel={exportMutation.isPending ? 'Enqueuing…' : 'Start export'}
        busy={exportMutation.isPending}
        error={adminError}
      >
        <label className="block space-y-1">
          <span className="text-[11px] uppercase tracking-[0.08em] text-ink-2">Container</span>
          <select
            value={targetContainer}
            onChange={(e) => setTargetContainer(e.target.value)}
            className="w-full rounded-lg border border-line-2 bg-white px-3 py-2 text-sm text-ink-1 focus:border-ink-1 focus:outline-none focus:ring-1 focus:ring-ink-1/30"
            disabled={availableContainers.length === 0}
          >
            {availableContainers.length === 0 && <option value="">No containers</option>}
            {availableContainers.map((container) => (
              <option key={container.id} value={container.id}>
                {container.name}
              </option>
            ))}
          </select>
        </label>

        <div className="flex gap-2" role="group" aria-label="Export format">
          {(
            [
              { value: 'tar', label: 'TAR', hint: 'Preferred for speed' },
              { value: 'zip', label: 'ZIP', hint: 'Compatible archives' },
            ] as const
          ).map((option) => (
            <label
              key={option.value}
              className={`flex-1 cursor-pointer rounded-xl border px-3 py-2 text-sm transition focus-within:ring-2 focus-within:ring-ink-1/30 ${
                exportFormat === option.value ? 'border-ink-1 bg-white' : 'border-line-2 bg-white/70'
              }`}
            >
              <div className="flex items-center gap-2">
                <input
                  type="radio"
                  name="export-format"
                  value={option.value}
                  checked={exportFormat === option.value}
                  onChange={() => setExportFormat(option.value)}
                  className="h-4 w-4 text-ink-1 focus:ring-ink-1/30"
                />
                <div>
                  <p className="font-medium text-ink-1">{option.label}</p>
                  <p className="text-xs text-ink-2">{option.hint}</p>
                </div>
              </div>
            </label>
          ))}
        </div>

        <div className="space-y-2">
          <label className="flex items-center gap-2 text-sm text-ink-1">
            <input
              type="checkbox"
              checked={includeVectors}
              onChange={(e) => setIncludeVectors(e.target.checked)}
              className="h-4 w-4 rounded border-ink-2/40 text-ink-1 focus:ring-ink-1/30"
            />
            Include vectors
          </label>
          <label className="flex items-center gap-2 text-sm text-ink-1">
            <input
              type="checkbox"
              checked={includeBlobs}
              onChange={(e) => setIncludeBlobs(e.target.checked)}
              className="h-4 w-4 rounded border-ink-2/40 text-ink-1 focus:ring-ink-1/30"
            />
            Include blobs
          </label>
          <p className="text-xs text-ink-2">Exports run as background jobs; progress shows in the maintenance panel.</p>
        </div>
      </AdminActionModal>
    </GlassShell>
  );
}
