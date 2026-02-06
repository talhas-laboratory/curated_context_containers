import { useMemo, useState } from 'react';
import type { ContainerSummary } from '../lib/types';

interface MultiContainerSelectorProps {
  containers: ContainerSummary[];
  selectedIds: string[];
  onChange: (ids: string[]) => void;
  disabled?: boolean;
  busy?: boolean;
  error?: string | null;
  maxVisibleBadges?: number;
}

export function MultiContainerSelector({
  containers,
  selectedIds,
  onChange,
  disabled = false,
  busy = false,
  error = null,
  maxVisibleBadges = 2,
}: MultiContainerSelectorProps) {
  const [open, setOpen] = useState(false);
  const [filter, setFilter] = useState('');

  const filtered = useMemo(() => {
    const q = filter.trim().toLowerCase();
    if (!q) return containers;
    return containers.filter(
      (c) =>
        c.name.toLowerCase().includes(q) ||
        (c.theme || '').toLowerCase().includes(q)
    );
  }, [containers, filter]);

  const visibleBadges = selectedIds.slice(0, maxVisibleBadges);
  const overflow = Math.max(selectedIds.length - maxVisibleBadges, 0);

  const toggleSelection = (id: string) => {
    if (selectedIds.includes(id)) {
      onChange(selectedIds.filter((s) => s !== id));
    } else {
      onChange([...selectedIds, id]);
    }
  };

  const selectAll = () => {
    const ids = filtered.map((c) => c.id);
    onChange(Array.from(new Set([...selectedIds, ...ids])));
  };

  const clearAll = () => onChange([]);

  return (
    <div className="relative" data-testid="multi-container-selector">
      <button
        type="button"
        aria-expanded={open}
        aria-haspopup="listbox"
        onClick={() => setOpen((prev) => !prev)}
        disabled={disabled || busy}
        className="flex items-center gap-2 rounded-full border border-line-2 bg-white/60 px-4 py-2 text-sm text-ink-1 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-line-1 disabled:cursor-not-allowed disabled:opacity-50"
      >
        <span className="font-medium">Containers</span>
        <div className="flex items-center gap-1">
          {visibleBadges.map((id) => {
            const label = containers.find((c) => c.id === id)?.name || id;
            return (
              <span
                key={id}
                className="rounded-full border border-line-2 bg-white px-2 py-0.5 text-xs text-ink-1"
              >
                {label}
              </span>
            );
          })}
          {overflow > 0 && (
            <span className="rounded-full border border-line-2 bg-white px-2 py-0.5 text-xs text-ink-2">
              +{overflow}
            </span>
          )}
        </div>
        {busy && (
          <span className="inline-flex h-4 w-4 animate-spin rounded-full border-2 border-line-2 border-t-ink-1" aria-hidden />
        )}
      </button>

      {open && (
        <div
          role="listbox"
          aria-label="Select containers"
          className="absolute z-30 mt-2 w-96 max-w-[90vw] rounded-2xl border border-line-2 bg-white p-4 shadow-sm"
        >
          <div className="flex items-center gap-2 mb-3">
            <label className="sr-only" htmlFor="container-filter">
              Filter containers
            </label>
            <input
              id="container-filter"
              type="text"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="Filter"
              className="w-full rounded-lg border border-line-2 px-3 py-2 text-sm text-ink-1 focus:border-ink-1 focus:outline-none focus:ring-1 focus:ring-line-1"
            />
          </div>

          {error && (
            <p className="mb-2 text-xs text-ember" role="alert">
              {error}
            </p>
          )}

          <div className="mb-3 flex items-center gap-2 text-xs text-ink-2">
            <button
              type="button"
              onClick={selectAll}
              className="rounded-full border border-line-2 px-2 py-1 hover:border-ink-1 hover:text-ink-1 transition"
            >
              Select all
            </button>
            <button
              type="button"
              onClick={clearAll}
              className="rounded-full border border-line-2 px-2 py-1 hover:border-ink-1 hover:text-ink-1 transition"
            >
              Clear
            </button>
          </div>

          <div className="max-h-80 overflow-y-auto space-y-1" data-testid="container-options">
            {filtered.length === 0 && (
              <p className="text-sm text-ink-2">No matches.</p>
            )}
            {filtered.map((container) => {
              const checked = selectedIds.includes(container.id);
              return (
                <label
                  key={container.id}
                  className="flex cursor-pointer items-center gap-3 rounded-lg px-2 py-2 hover:bg-paper-0"
                >
                  <input
                    type="checkbox"
                    className="h-4 w-4 rounded border-ink-2/40 text-ink-1 focus:ring-ink-1/30"
                    checked={checked}
                    onChange={() => toggleSelection(container.id)}
                    aria-label={container.name}
                  />
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-ink-1">{container.name}</span>
                      <span className="text-[11px] uppercase tracking-[0.08em] text-ink-2">
                        {container.theme || '—'}
                      </span>
                    </div>
                    <div className="text-xs text-ink-2">
                      {container.modalities.join(', ')}
                    </div>
                  </div>
                </label>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
