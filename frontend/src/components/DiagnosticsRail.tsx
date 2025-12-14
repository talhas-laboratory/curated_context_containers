'use client';

import { DiagnosticsPayload, GoldenQuerySummary, TimingBreakdown } from './types';
import { GlassCard } from './glass/GlassCard';

interface DiagnosticsRailProps {
  diagnostics?: DiagnosticsPayload | null;
  timings?: TimingBreakdown | null;
  goldenSummary?: GoldenQuerySummary | null;
  visible?: boolean;
}

const numberFormatter = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 });

export function DiagnosticsRail({ diagnostics, timings, goldenSummary, visible = true }: DiagnosticsRailProps) {
  if (!visible) {
    return null;
  }

  return (
    <aside
      className="w-full lg:w-72 shrink-0"
      aria-label="Search diagnostics"
      data-testid="diagnostics-rail"
    >
      <GlassCard className="space-y-6 !p-5 bg-white/40 backdrop-blur-md border-white/30 sticky top-32">
        <header className="flex items-center justify-between border-b border-white/20 pb-4">
          <div>
            <p className="text-[10px] uppercase tracking-[0.2em] text-ink-2 mb-1">Mode</p>
            <p className="font-serif text-lg text-ink-1">{diagnostics?.mode ?? '—'}</p>
          </div>
          <div className="text-right">
            <p className="text-[10px] uppercase tracking-[0.2em] text-ink-2 mb-1">Latency</p>
            <p
              className={`font-mono text-lg ${
                (diagnostics?.latency_over_budget_ms ?? 0) > 0 ? 'text-ember' : 'text-ink-1'
              }`}
            >
              {timings?.total_ms ? `${numberFormatter.format(timings.total_ms)}ms` : '—'}
            </p>
          </div>
        </header>

        <dl className="grid grid-cols-2 gap-4 text-xs">
          <div className="bg-white/30 rounded-lg p-2 border border-white/20">
            <dt className="text-ink-2 mb-1">BM25 Hits</dt>
            <dd className="font-mono font-semibold text-ink-1">{diagnostics?.bm25_hits ?? '—'}</dd>
          </div>
          <div className="bg-white/30 rounded-lg p-2 border border-white/20">
            <dt className="text-ink-2 mb-1">Vector Hits</dt>
            <dd className="font-mono font-semibold text-ink-1">{diagnostics?.vector_hits ?? '—'}</dd>
          </div>
          <div className="col-span-2 flex justify-between items-center bg-white/20 rounded-lg p-2 border border-white/10">
            <dt className="text-ink-2">Latency Budget</dt>
            <dd className="font-mono text-ink-1">{diagnostics?.latency_budget_ms ?? '—'}ms</dd>
          </div>
        </dl>

        {timings && (
          <section>
            <p className="mb-3 text-[10px] uppercase tracking-[0.2em] text-ink-2 opacity-70">Stage Timings</p>
            <div className="space-y-1.5">
              {Object.entries(timings).map(([stage, value]) => (
                <div key={stage} className="flex justify-between text-xs items-center group">
                  <span className="text-ink-2 group-hover:text-ink-1 transition-colors">{stage.replace('_ms', '')}</span>
                  <div className="flex items-center gap-2">
                     <div className="h-1 bg-blue-100 rounded-full overflow-hidden w-16 opacity-50">
                        <div 
                          className="h-full bg-blue-400 rounded-full" 
                          style={{ width: `${Math.min(100, (value / (timings.total_ms || 1)) * 100)}%` }}
                        />
                     </div>
                     <span className="font-mono w-10 text-right opacity-70">{value ? `${numberFormatter.format(value)}` : '-'}</span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}
      </GlassCard>
    </aside>
  );
}
