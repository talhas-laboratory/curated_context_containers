'use client';

import { useEffect, useRef, useState } from 'react';
import { useParams } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';

import { GlassShell } from '../../../../components/glass/GlassShell';
import { GlassCard } from '../../../../components/glass/GlassCard';
import { GlassInput } from '../../../../components/glass/GlassInput';
import { ResultItem } from '../../../../components/ResultItem';
import { DiagnosticsRail } from '../../../../components/DiagnosticsRail';
import { DocumentModal } from '../../../../components/DocumentModal';
import { ContainerDocumentsPanel } from '../../../../components/ContainerDocumentsPanel';
import { useDescribeContainer } from '../../../../lib/hooks/use-containers';
import { useSearch } from '../../../../lib/hooks/use-search';
import type { SearchResult } from '../../../../lib/types';
import { useKeyboardShortcuts } from '../../../../lib/keyboard';

const MODES: Array<{ label: string; value: 'semantic' | 'hybrid' | 'bm25' }> = [
  { label: 'Hybrid', value: 'hybrid' },
  { label: 'Semantic', value: 'semantic' },
  { label: 'BM25', value: 'bm25' },
];

export default function ContainerSearchPage() {
  const params = useParams<{ id: string }>();
  const containerId = params?.id;
  const searchInputRef = useRef<HTMLInputElement>(null);

  const [query, setQuery] = useState('');
  const [mode, setMode] = useState<'semantic' | 'hybrid' | 'bm25'>('hybrid');
  const [k, setK] = useState(10);
  const [diagnosticsEnabled, setDiagnosticsEnabled] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [activeResult, setActiveResult] = useState<SearchResult | null>(null);

  const {
    data: containerDetail,
    isLoading: containerLoading,
    error: containerError,
  } = useDescribeContainer(containerId || '');
  const { mutate: runSearch, data: searchData, isPending: searching, error: searchError } = useSearch();

  const results = searchData?.results || [];
  const diagnostics = searchData?.diagnostics;
  const timings = searchData?.timings_ms;
  const issues = searchData?.issues || [];

  useEffect(() => {
    setSelectedIndex(0);
  }, [searchData]);

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
    if (!query || !containerId) {
      console.warn('Search blocked: missing query or containerId', { query, containerId });
      return;
    }
    console.log('Running search...');
    runSearch({
      query,
      containerIds: [containerId],
      mode,
      k,
      diagnostics: diagnosticsEnabled,
    });
  };

  const showEmptyState = !searching && searchData && results.length === 0;
  const showInitialState = !searching && !searchData && !searchError;
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
               placeholder={`Search ${containerDetail?.container.name ?? 'container'}…`}
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
                <div className="flex gap-2 bg-white/40 rounded-full p-1 backdrop-blur-sm border border-white/30">
                  {MODES.map((m) => (
                    <button
                      key={m.value}
                      onClick={() => setMode(m.value)}
                      className={`px-4 py-1.5 rounded-full text-sm transition-all duration-300 ${
                        mode === m.value
                          ? 'bg-white text-ink-1 shadow-sm font-medium'
                          : 'text-ink-2 hover:text-ink-1 hover:bg-white/50'
                      }`}
                    >
                      {m.label}
                    </button>
                  ))}
                </div>

                <div className="flex items-center gap-4">
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
                </div>
              </div>

              {/* Issues & Errors */}
              {(issues.length > 0 || searchError) && (
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
                  {searchError && (
                    <p className="text-red-600">{(searchError as Error).message || 'Search error'}</p>
                  )}
                </motion.div>
              )}

              {/* Results List */}
              <div className="space-y-4 min-h-[200px]">
                {searching && (
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
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, scale: 0.95 }}
                      transition={{ delay: idx * 0.05 }}
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
              </div>
           </div>
        </div>
      </div>

      <DocumentModal result={activeResult} isOpen={!!activeResult} onClose={() => setActiveResult(null)} />
    </GlassShell>
  );
}
