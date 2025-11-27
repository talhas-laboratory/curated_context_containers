'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { useListContainers } from '../../lib/hooks/use-containers';
import { GlassShell } from '../../components/glass/GlassShell';
import { GlassCard } from '../../components/glass/GlassCard';
import Link from 'next/link';

export default function ContainersPage() {
  const [stateFilter, setStateFilter] = useState<'active' | 'all'>('active');
  const { data, isLoading, isError, error, refetch } = useListContainers(
    stateFilter === 'all' ? 'all' : 'active'
  );

  return (
    <GlassShell 
      headline="Containers" 
      description="Curated, theme-scoped vector collections."
    >
      <div className="space-y-8">
        {/* Filters */}
        <div className="flex gap-2 border-b border-line-1/50 pb-4">
            <button
              onClick={() => setStateFilter('active')}
              className={`px-4 py-2 rounded-full text-sm transition-all duration-300 ${
                stateFilter === 'active'
                  ? 'bg-white text-ink-1 shadow-glass font-medium'
                  : 'text-ink-2 hover:text-ink-1 hover:bg-white/40'
              }`}
            >
              Active
            </button>
            <button
              onClick={() => setStateFilter('all')}
              className={`px-4 py-2 rounded-full text-sm transition-all duration-300 ${
                stateFilter === 'all'
                  ? 'bg-white text-ink-1 shadow-glass font-medium'
                  : 'text-ink-2 hover:text-ink-1 hover:bg-white/40'
              }`}
            >
              All
            </button>
        </div>

        {/* Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {isLoading && [1, 2, 3].map((i) => (
             <GlassCard key={i} className="h-48 animate-pulse bg-white/20 border-white/10">
                <div className="w-2/3 h-6 bg-white/20 rounded mb-4"/>
                <div className="w-full h-4 bg-white/10 rounded mb-2"/>
                <div className="w-1/2 h-4 bg-white/10 rounded"/>
             </GlassCard>
          ))}

          {isError && (
             <div className="col-span-full text-center py-12">
               <p className="text-ember mb-4">Failed to load containers.</p>
               <button 
                 onClick={() => refetch()}
                 className="px-6 py-2 bg-white shadow-sm rounded-full text-sm hover:bg-gray-50 transition"
               >
                 Retry
               </button>
             </div>
          )}

          {data?.containers.map((container) => (
            <Link key={container.id} href={`/containers/${container.id}/search`}>
              <GlassCard className="h-full group cursor-pointer relative overflow-hidden">
                 <div className="absolute top-0 right-0 p-4 opacity-0 group-hover:opacity-100 transition-opacity duration-500">
                   <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-ink-2">
                     <path d="M5 12h14" />
                     <path d="m12 5 7 7-7 7" />
                   </svg>
                 </div>

                 <h3 className="font-serif text-xl text-ink-1 mb-2 group-hover:text-blue-600 transition-colors">
                   {container.name}
                 </h3>
                 <p className="text-sm text-ink-2 mb-6 line-clamp-2">
                   {container.theme || 'No theme defined'}
                 </p>

                 <div className="mt-auto pt-4 border-t border-line-1/30 flex items-center justify-between text-xs text-ink-2 font-mono">
                   <span>{container.stats.document_count} docs</span>
                   <span>{container.stats.chunk_count} chunks</span>
                 </div>
                 
                 <div className="absolute bottom-0 left-0 w-full h-1 bg-gradient-to-r from-blue-400/0 via-blue-400/40 to-purple-400/0 transform scale-x-0 group-hover:scale-x-100 transition-transform duration-500"/>
              </GlassCard>
            </Link>
          ))}
        </div>
      </div>
    </GlassShell>
  );
}
