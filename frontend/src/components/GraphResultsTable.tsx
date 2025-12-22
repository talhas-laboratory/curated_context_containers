import React, { useMemo } from 'react';

interface GraphResultItem {
  id?: string;
  node_id?: string;
  label?: string | null;
  type?: string | null;
  summary?: string | null;
  source?: string;
  target?: string;
  source_chunk_ids?: string[];
}

interface GraphSnippet {
  chunk_id: string;
  doc_id?: string;
  uri?: string | null;
  title?: string | null;
  text?: string | null;
}

interface GraphResultsTableProps {
  nodes: GraphResultItem[];
  edges: GraphResultItem[];
  snippets: GraphSnippet[];
  maxHops?: number;
}

export function GraphResultsTable({ nodes, edges, snippets, maxHops }: GraphResultsTableProps) {
  const snippetMap = useMemo(() => {
    const map = new Map<string, GraphSnippet>();
    snippets.forEach((snippet) => {
      if (snippet?.chunk_id) {
        map.set(snippet.chunk_id, snippet);
      }
    });
    return map;
  }, [snippets]);

  const renderProvenance = (chunkIds: string[] | undefined) => {
    const ids = chunkIds || [];
    if (!ids.length) return '—';
    const labels = ids.slice(0, 3).map((cid) => {
      const snippet = snippetMap.get(cid);
      return snippet?.title || snippet?.uri || cid;
    });
    return labels.join(', ');
  };

  if (!nodes.length && !edges.length && !snippets.length) {
    return null;
  }

  return (
    <div className="rounded-xl border border-line-2 bg-white px-4 py-3 space-y-3" data-testid="graph-context">
      <div className="flex items-center justify-between">
        <p className="text-sm uppercase tracking-[0.08em] text-ink-2">Graph context</p>
        <span className="text-xs text-ink-2">hops ≤ {maxHops ?? '—'}</span>
      </div>
      {nodes.length ? (
        <div className="space-y-2">
          <p className="text-sm font-medium text-ink-1">Nodes</p>
          <div className="overflow-x-auto" role="region" aria-label="Graph nodes table">
            <table className="w-full text-sm text-ink-1 border-collapse">
              <thead className="text-ink-2">
                <tr className="border-b border-line-1">
                  <th className="text-left py-2 pr-3 font-normal">Label</th>
                  <th className="text-left py-2 pr-3 font-normal">Type</th>
                  <th className="text-left py-2 pr-3 font-normal">Summary</th>
                  <th className="text-left py-2 pr-3 font-normal">Provenance</th>
                </tr>
              </thead>
              <tbody>
                {nodes.slice(0, 20).map((node, idx) => (
                  <tr key={idx} className="border-b border-line-1/60 last:border-0">
                    <td className="py-2 pr-3">{node.label || node.id || node.node_id}</td>
                    <td className="py-2 pr-3 text-ink-2">{node.type || '—'}</td>
                    <td className="py-2 pr-3 text-ink-2">{node.summary || '—'}</td>
                    <td className="py-2 pr-3 text-ink-2">{renderProvenance(node.source_chunk_ids)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
      {edges.length ? (
        <div className="space-y-2">
          <p className="text-sm font-medium text-ink-1">Edges</p>
          <div className="overflow-x-auto" role="region" aria-label="Graph edges table">
            <table className="w-full text-sm text-ink-1 border-collapse">
              <thead className="text-ink-2">
                <tr className="border-b border-line-1">
                  <th className="text-left py-2 pr-3 font-normal">Source</th>
                  <th className="text-left py-2 pr-3 font-normal">Type</th>
                  <th className="text-left py-2 pr-3 font-normal">Target</th>
                  <th className="text-left py-2 pr-3 font-normal">Provenance</th>
                </tr>
              </thead>
              <tbody>
                {edges.slice(0, 20).map((edge, idx) => (
                  <tr key={idx} className="border-b border-line-1/60 last:border-0">
                    <td className="py-2 pr-3">{edge.source}</td>
                    <td className="py-2 pr-3 text-ink-2">{edge.type || '—'}</td>
                    <td className="py-2 pr-3">{edge.target}</td>
                    <td className="py-2 pr-3 text-ink-2">{renderProvenance(edge.source_chunk_ids)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
      {snippets.length ? (
        <div className="space-y-2">
          <p className="text-sm font-medium text-ink-1">Snippets</p>
          <div className="overflow-x-auto" role="region" aria-label="Graph snippets table">
            <table className="w-full text-sm text-ink-1 border-collapse">
              <thead className="text-ink-2">
                <tr className="border-b border-line-1">
                  <th className="text-left py-2 pr-3 font-normal">Title / URI</th>
                  <th className="text-left py-2 pr-3 font-normal">Chunk</th>
                  <th className="text-left py-2 pr-3 font-normal">Preview</th>
                </tr>
              </thead>
              <tbody>
                {snippets.slice(0, 20).map((snippet, idx) => (
                  <tr key={idx} className="border-b border-line-1/60 last:border-0">
                    <td className="py-2 pr-3 text-ink-2">{snippet.title || snippet.uri || '—'}</td>
                    <td className="py-2 pr-3 text-ink-2 font-mono text-[11px]">{snippet.chunk_id}</td>
                    <td className="py-2 pr-3 text-ink-2">{(snippet.text || '').slice(0, 200) || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
    </div>
  );
}
