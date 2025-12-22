import React from 'react';

interface GraphDiagnosticsBarProps {
  graphMs?: number;
  graphHits?: number;
  modeLabel?: string;
  issues?: string[];
}

export function GraphDiagnosticsBar({ graphMs, graphHits, modeLabel, issues }: GraphDiagnosticsBarProps) {
  if (graphMs === undefined && graphHits === undefined && (!issues || issues.length === 0) && !modeLabel) {
    return null;
  }
  return (
    <div
      className="flex flex-wrap gap-2 text-[11px] text-ink-2"
      role="status"
      aria-live="polite"
      aria-label="Graph diagnostics"
    >
      <span className="px-2 py-1 rounded-full border border-line-2 bg-white/70">graph_ms: {graphMs ?? '—'}</span>
      <span className="px-2 py-1 rounded-full border border-line-2 bg-white/70">graph_hits: {graphHits ?? '—'}</span>
      {modeLabel ? (
        <span className="px-2 py-1 rounded-full border border-line-2 bg-white/70">mode: {modeLabel}</span>
      ) : null}
      {issues?.length
        ? issues.map((issue) => (
            <span
              key={issue}
              className="px-2 py-1 bg-white/60 rounded-md text-ember border border-ember/40 text-xs font-mono"
            >
              {issue}
            </span>
          ))
        : null}
    </div>
  );
}
