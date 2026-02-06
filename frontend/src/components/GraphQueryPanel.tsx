import React from 'react';

interface GraphQueryPanelProps {
  mode: string;
  rawCypherEnabled: boolean;
  rawCypher: string;
  onToggleRawCypher: (enabled: boolean) => void;
  onChangeRawCypher: (value: string) => void;
  onSubmit?: () => void;
}

export function GraphQueryPanel({
  mode,
  rawCypherEnabled,
  rawCypher,
  onToggleRawCypher,
  onChangeRawCypher,
  onSubmit,
}: GraphQueryPanelProps) {
  if (mode !== 'graph') return null;
  return (
    <div className="space-y-2" aria-label="Graph query panel">
      <label className="flex items-center gap-2 text-sm text-ink-2 cursor-pointer select-none">
        <input
          type="checkbox"
          checked={rawCypherEnabled}
          onChange={(e) => onToggleRawCypher(e.target.checked)}
          className="rounded border-ink-2/30 text-ink-1 focus:ring-ink-1/20"
          aria-label="Toggle raw Cypher"
        />
        Raw Cypher
      </label>
      {rawCypherEnabled ? (
        <div className="space-y-2">
          <label className="text-[11px] uppercase tracking-[0.08em] text-ink-2" htmlFor="raw-cypher">
            Raw Cypher
          </label>
          <textarea
            id="raw-cypher"
            value={rawCypher}
            onChange={(e) => onChangeRawCypher(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                onSubmit?.();
              }
              if (e.key === 'Escape') {
                onToggleRawCypher(false);
              }
            }}
            rows={4}
            className="w-full rounded-lg border border-line-2 bg-white px-3 py-2 text-sm text-ink-1 focus:border-ink-1 focus:outline-none focus:ring-1 focus:ring-ink-1/30"
            placeholder="MATCH (n)-[r]->(m) RETURN n,r,m LIMIT 20"
            aria-label="Raw Cypher input"
          />
        </div>
      ) : null}
    </div>
  );
}
