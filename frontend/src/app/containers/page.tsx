'use client';

import { FormEvent, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useCreateContainer, useListContainers } from '../../lib/hooks/use-containers';
import { GlassShell } from '../../components/glass/GlassShell';
import { GlassCard } from '../../components/glass/GlassCard';
import Link from 'next/link';
import type { CreateContainerRequest } from '../../lib/types';

export default function ContainersPage() {
  const router = useRouter();
  const [stateFilter, setStateFilter] = useState<'active' | 'all'>('active');
  const [createError, setCreateError] = useState<string | null>(null);
  const [createSuccess, setCreateSuccess] = useState<string | null>(null);
  const [form, setForm] = useState<CreateContainerRequest>({
    name: '',
    theme: '',
    description: '',
    mission_context: '',
    modalities: ['text'],
    visibility: 'private',
    collaboration_policy: 'contribute',
    auto_refresh: false,
    embedder: 'google-gemma3-text',
    embedder_version: '1.0.0',
    dims: 768,
  });

  const { data, isLoading, isError, refetch } = useListContainers(
    stateFilter === 'all' ? 'all' : 'active'
  );
  const { mutateAsync: createContainer, isPending: isCreating } = useCreateContainer();

  const toggleModality = (modality: string) => {
    setForm((prev) => {
      const current = prev.modalities || [];
      const exists = current.includes(modality);
      const next = exists ? current.filter((m) => m !== modality) : [...current, modality];
      return { ...prev, modalities: next.length ? next : ['text'] };
    });
  };

  const handleCreate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setCreateError(null);
    setCreateSuccess(null);

    const name = form.name.trim();
    const theme = form.theme.trim();
    if (!name || !theme) {
      setCreateError('Name and theme are required.');
      return;
    }

    const payload: CreateContainerRequest = {
      ...form,
      name,
      theme,
      description: form.description?.trim() || undefined,
      mission_context: form.mission_context?.trim() || undefined,
      modalities: form.modalities?.length ? form.modalities : ['text'],
      embedder: form.embedder?.trim() || undefined,
      embedder_version: form.embedder_version?.trim() || undefined,
    };

    try {
      const response = await createContainer(payload);
      setCreateSuccess(response.message ?? 'Container created');
      setForm((prev) => ({
        ...prev,
        name: '',
        theme: '',
        description: '',
        mission_context: '',
        modalities: ['text'],
        auto_refresh: false,
      }));

      if (response.container_id) {
        router.push(`/containers/${response.container_id}/search`);
      }
    } catch (err: any) {
      const message = err?.message || 'Failed to create container.';
      setCreateError(message);
    }
  };

  return (
    <GlassShell 
      headline="Containers" 
      description="Curated, theme-scoped vector collections."
    >
      <div className="space-y-8">
        <GlassCard className="col-span-full bg-gradient-to-r from-white/70 to-white/40 border border-white/40 shadow-glass" hoverEffect={false}>
          <div className="flex flex-col gap-4">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-ink-1">Spin up a new container</p>
                <p className="text-xs text-ink-2">Name it, set a theme, and choose allowed modalities.</p>
              </div>
              {createSuccess && <span className="text-xs text-green-700 bg-green-50 border border-green-200 px-3 py-1 rounded-full">{createSuccess}</span>}
              {createError && <span className="text-xs text-ember bg-amber-50 border border-amber-200 px-3 py-1 rounded-full">{createError}</span>}
            </div>

            <form className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" onSubmit={handleCreate}>
              <label className="space-y-2">
                <span className="text-xs uppercase tracking-wide text-ink-2">Name</span>
                <input
                  required
                  value={form.name}
                  onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
                  placeholder="expressionist-art"
                  className="w-full rounded-xl border border-white/30 bg-white/90 px-3 py-2 text-sm text-ink-1 placeholder:text-ink-2/70 shadow-inner focus:outline-none focus:ring-2 focus:ring-blue-300/70"
                />
              </label>

              <label className="space-y-2">
                <span className="text-xs uppercase tracking-wide text-ink-2">Theme</span>
                <input
                  required
                  value={form.theme}
                  onChange={(e) => setForm((prev) => ({ ...prev, theme: e.target.value }))}
                  placeholder="Expressionism, neural networks, policy docs..."
                  className="w-full rounded-xl border border-white/30 bg-white/90 px-3 py-2 text-sm text-ink-1 placeholder:text-ink-2/70 shadow-inner focus:outline-none focus:ring-2 focus:ring-blue-300/70"
                />
              </label>

              <label className="space-y-2">
                <span className="text-xs uppercase tracking-wide text-ink-2">Embedder</span>
                <input
                  value={form.embedder}
                  onChange={(e) => setForm((prev) => ({ ...prev, embedder: e.target.value }))}
                  placeholder="google-gemma3-text"
                  className="w-full rounded-xl border border-white/30 bg-white/90 px-3 py-2 text-sm text-ink-1 placeholder:text-ink-2/70 shadow-inner focus:outline-none focus:ring-2 focus:ring-blue-300/70"
                />
              </label>

              <label className="space-y-2 lg:col-span-2">
                <span className="text-xs uppercase tracking-wide text-ink-2">Description</span>
                <textarea
                  value={form.description}
                  onChange={(e) => setForm((prev) => ({ ...prev, description: e.target.value }))}
                  placeholder="What belongs here? Who is it for?"
                  className="w-full rounded-xl border border-white/30 bg-white/90 px-3 py-2 text-sm text-ink-1 placeholder:text-ink-2/70 shadow-inner focus:outline-none focus:ring-2 focus:ring-blue-300/70 min-h-[64px]"
                />
              </label>

              <label className="space-y-2">
                <span className="text-xs uppercase tracking-wide text-ink-2">Mission context</span>
                <textarea
                  value={form.mission_context}
                  onChange={(e) => setForm((prev) => ({ ...prev, mission_context: e.target.value }))}
                  placeholder="Why does this container exist?"
                  className="w-full rounded-xl border border-white/30 bg-white/90 px-3 py-2 text-sm text-ink-1 placeholder:text-ink-2/70 shadow-inner focus:outline-none focus:ring-2 focus:ring-blue-300/70 min-h-[64px]"
                />
              </label>

              <div className="space-y-2">
                <span className="text-xs uppercase tracking-wide text-ink-2">Modalities</span>
                <div className="flex flex-wrap gap-2">
                  {['text', 'image', 'pdf'].map((modality) => {
                    const checked = form.modalities?.includes(modality);
                    return (
                      <label
                        key={modality}
                        className={`px-3 py-2 rounded-full border text-xs cursor-pointer transition ${
                          checked
                            ? 'bg-blue-600 text-white border-blue-500 shadow-glass'
                            : 'bg-white/80 text-ink-1 border-white/40 hover:border-blue-300'
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => toggleModality(modality)}
                          className="sr-only"
                        />
                        {modality}
                      </label>
                    );
                  })}
                </div>
              </div>

              <label className="space-y-2">
                <span className="text-xs uppercase tracking-wide text-ink-2">Visibility</span>
                <select
                  value={form.visibility}
                  onChange={(e) => setForm((prev) => ({ ...prev, visibility: e.target.value as CreateContainerRequest['visibility'] }))}
                  className="w-full rounded-xl border border-white/30 bg-white/90 px-3 py-2 text-sm text-ink-1 shadow-inner focus:outline-none focus:ring-2 focus:ring-blue-300/70"
                >
                  <option value="private">Private</option>
                  <option value="team">Team</option>
                  <option value="public">Public</option>
                </select>
              </label>

              <label className="space-y-2">
                <span className="text-xs uppercase tracking-wide text-ink-2">Collaboration</span>
                <select
                  value={form.collaboration_policy}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      collaboration_policy: e.target.value as CreateContainerRequest['collaboration_policy'],
                    }))
                  }
                  className="w-full rounded-xl border border-white/30 bg-white/90 px-3 py-2 text-sm text-ink-1 shadow-inner focus:outline-none focus:ring-2 focus:ring-blue-300/70"
                >
                  <option value="contribute">Contribute</option>
                  <option value="read-only">Read only</option>
                </select>
              </label>

              <div className="flex items-center gap-3">
                <label className="flex items-center gap-2 text-sm text-ink-1">
                  <input
                    type="checkbox"
                    checked={form.auto_refresh}
                    onChange={(e) => setForm((prev) => ({ ...prev, auto_refresh: e.target.checked }))}
                    className="h-4 w-4 rounded border-white/30 text-blue-600 focus:ring-blue-500"
                  />
                  Auto-refresh from manifests
                </label>
              </div>

              <div className="flex items-end justify-start">
                <button
                  type="submit"
                  disabled={isCreating}
                  className="inline-flex items-center gap-2 px-5 py-2 rounded-full bg-gradient-to-r from-blue-600 to-indigo-600 text-white text-sm font-medium shadow-glass disabled:opacity-60 disabled:cursor-not-allowed hover:shadow-lg transition"
                >
                  {isCreating ? 'Creating…' : 'Create container'}
                </button>
              </div>
            </form>
          </div>
        </GlassCard>

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
                   <span>{container.stats?.document_count ?? 0} docs</span>
                   <span>{container.stats?.chunk_count ?? 0} chunks</span>
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
