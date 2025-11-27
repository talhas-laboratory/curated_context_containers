'use client';

import { useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useQueryClient } from '@tanstack/react-query';

import { GlassCard } from './glass/GlassCard';
import { useContainerDocuments, useDeleteDocument } from '../lib/hooks/use-documents';

interface ContainerDocumentsPanelProps {
  containerId?: string;
}

export function ContainerDocumentsPanel({ containerId }: ContainerDocumentsPanelProps) {
  const [search, setSearch] = useState('');
  const searchParam = useMemo(() => search.trim() || undefined, [search]);
  const queryClient = useQueryClient();

  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
  } = useContainerDocuments(containerId, { search: searchParam, limit: 25 });

  const deleteMutation = useDeleteDocument(
    () => {
      refetch();
      if (containerId) {
        queryClient.invalidateQueries({ queryKey: ['containers', 'describe', containerId] });
      }
      queryClient.invalidateQueries({ queryKey: ['containers', 'list'] });
    },
    () => undefined
  );

  const documents = data?.documents ?? [];

  const handleDelete = (documentId: string) => {
    if (!containerId) return;
    if (typeof window !== 'undefined') {
      const confirmed = window.confirm('Remove this document from the container?');
      if (!confirmed) {
        return;
      }
    }
    deleteMutation.mutate({ container: containerId, document_id: documentId });
  };

  return (
    <GlassCard className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <div>
          <p className="text-xs uppercase tracking-wide text-ink-2">Documents</p>
          <h3 className="text-lg font-serif text-ink-1">
            {documents.length} item{documents.length === 1 ? '' : 's'}
          </h3>
        </div>
        <input
          type="search"
          placeholder="Filter"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="rounded-full border border-line-1/70 bg-white/60 px-3 py-1 text-xs text-ink-1 placeholder:text-ink-2 focus:border-ink-1 focus:outline-none"
        />
      </div>

      {isLoading && (
        <div className="text-xs text-ink-2">Loading documents…</div>
      )}

      {isError && (
        <div className="text-xs text-ember">
          Failed to load documents{error?.message ? `: ${error.message}` : ''}.
        </div>
      )}

      {!isLoading && documents.length === 0 && (
        <p className="text-sm text-ink-2">No documents found.</p>
      )}

      <div className="space-y-3">
        <AnimatePresence>
          {documents.map((doc) => (
            <motion.div
              key={doc.id}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              className="rounded-2xl border border-line-1/70 bg-white/70 p-3 text-sm"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-medium text-ink-1">
                    {doc.title || doc.uri || 'Untitled document'}
                  </p>
                  <p className="text-xs text-ink-2">
                    {doc.chunk_count} chunk{doc.chunk_count === 1 ? '' : 's'} ·{' '}
                    {new Date(doc.updated_at).toLocaleDateString()}
                  </p>
                </div>
                <button
                  onClick={() => handleDelete(doc.id)}
                  className="rounded-full border border-line-2 px-3 py-1 text-xs uppercase tracking-wide text-ink-2 transition hover:border-ink-1 hover:text-ink-1"
                  disabled={deleteMutation.isPending && deleteMutation.variables?.document_id === doc.id}
                >
                  {deleteMutation.isPending && deleteMutation.variables?.document_id === doc.id
                    ? 'Removing…'
                    : 'Remove'}
                </button>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </GlassCard>
  );
}

