'use client';

import type { SearchResult } from '../lib/types';
import { GlassCard } from './glass/GlassCard';

interface ResultItemProps {
  result: SearchResult;
  diagnosticsVisible?: boolean;
  onSelect?: (result: SearchResult) => void;
  selected?: boolean;
}

const numberFormatter = new Intl.NumberFormat('en-US', {
  maximumFractionDigits: 2,
});

export function ResultItem({ result, diagnosticsVisible = false, onSelect, selected = false }: ResultItemProps) {
  const handleClick = () => {
    if (onSelect) {
      onSelect(result);
    }
  };

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={handleClick}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          handleClick();
        }
      }}
      className="outline-none group"
      data-testid="result-item"
    >
      <GlassCard 
        hoverEffect={true}
        className={`
           cursor-pointer transition-all duration-300 border
           ${selected ? 'bg-white/80 border-blue-300 ring-1 ring-blue-100 shadow-glass-glow' : 'border-white/20 hover:border-white/40'}
        `}
      >
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-2 w-full">
            <div className="flex items-center justify-between">
              <p className="text-[10px] uppercase tracking-[0.2em] text-ink-2/60 font-medium">
                {result.container_name ?? result.container_id}
              </p>
              {diagnosticsVisible && typeof result.score === 'number' && (
                <span className={`
                  px-2 py-0.5 rounded-full text-[10px] font-mono border
                  ${result.score > 0.8 ? 'bg-blue-50/50 text-blue-600 border-blue-100' : 'bg-gray-50/50 text-gray-500 border-gray-100'}
                `}>
                  {numberFormatter.format(result.score)}
                </span>
              )}
            </div>

            <h3 className="font-serif text-lg text-ink-1 leading-tight group-hover:text-blue-700 transition-colors">
              {result.title ?? 'Untitled document'}
            </h3>
            
            <div className="relative pl-3 border-l-2 border-line-2/50 group-hover:border-blue-200 transition-colors">
               <p className="text-sm text-ink-2 leading-relaxed line-clamp-3 font-light">
                 {result.snippet}
               </p>
            </div>
          </div>
        </div>

        <div className="mt-4 pt-3 border-t border-line-1/20 flex flex-wrap items-center gap-3 text-[10px] text-ink-2/50 uppercase tracking-wider">
           {result.modality && (
             <span className="px-1.5 py-0.5 bg-white/40 rounded border border-white/30">
               {result.modality}
             </span>
           )}
           {result.provenance?.ingested_at && (
             <span>{new Date(result.provenance.ingested_at as string).toLocaleDateString()}</span>
           )}
        </div>
      </GlassCard>
    </div>
  );
}
