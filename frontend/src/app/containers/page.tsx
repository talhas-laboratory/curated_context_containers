'use client';

import { FormEvent, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useCreateContainer, useDeleteContainer, useListContainers } from '../../lib/hooks/use-containers';
import { GlassShell } from '../../components/glass/GlassShell';
import { GlassCard } from '../../components/glass/GlassCard';
import { AdminActionModal } from '../../components/AdminActionModal';
import Link from 'next/link';
import type { ContainerSummary, CreateContainerRequest } from '../../lib/types';

export default function ContainersPage() {
  const router = useRouter();
  const [stateFilter, setStateFilter] = useState<'active' | 'all'>('active');
  const [createError, setCreateError] = useState<string | null>(null);
  const [createSuccess, setCreateSuccess] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<ContainerSummary | null>(null);
  const [deletePermanent, setDeletePermanent] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deleteSuccess, setDeleteSuccess] = useState<string | null>(null);
  const [form, setForm] = useState<CreateContainerRequest>({
    name: '',
    theme: '',
    parent_id: '',
    description: '',
    mission_context: '',
    modalities: ['text', 'pdf', 'image'],
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
  const { mutateAsync: deleteContainer, isPending: isDeleting } = useDeleteContainer();

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
      parent_id: form.parent_id?.trim() || undefined,
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
        parent_id: '',
        description: '',
        mission_context: '',
        modalities: ['text', 'pdf', 'image'],
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

  const openDeleteModal = (container: ContainerSummary) => {
    setDeleteTarget(container);
    setDeletePermanent(container.state === 'archived');
    setDeleteError(null);
    setDeleteSuccess(null);
  };

  const handleDelete = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!deleteTarget) return;
    setDeleteError(null);
    try {
      const response = await deleteContainer({
        container: deleteTarget.id,
        permanent: deletePermanent,
      });
      setDeleteSuccess(response.message ?? 'Container updated');
      setDeleteTarget(null);
      setDeletePermanent(false);
    } catch (err: any) {
      const message = err?.message || 'Failed to delete container.';
      setDeleteError(message);
    }
  };

  const containers = data?.containers || [];
  const containerById = new Map(containers.map((container) => [container.id, container]));
  const childrenByParent = containers.reduce<Record<string, ContainerSummary[]>>((acc, container) => {
    if (container.parent_id) {
      const key = container.parent_id;
      if (!acc[key]) acc[key] = [];
      acc[key].push(container);
    }
    return acc;
  }, {});
  const rootContainers = containers.filter(
    (container) => !container.parent_id || !containerById.has(container.parent_id)
  );
  const parentOptions = containers
    .filter((container) => container.state !== 'archived')
    .sort((a, b) => a.name.localeCompare(b.name));

  const renderCard = (
    container: ContainerSummary,
    options?: { compact?: boolean; parentName?: string }
  ) => {
    const compact = options?.compact;
    const parentName = options?.parentName;

    return (
      <div key={container.id} className="group relative">
        <Link href={`/containers/${container.id}/search`} className="block h-full">
          <GlassCard className={`h-full cursor-pointer relative overflow-hidden ${compact ? 'p-5' : ''}`}>
            <div className="absolute top-0 right-0 p-4 opacity-0 group-hover:opacity-100 transition-opacity duration-500">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-ink-2">
                <path d="M5 12h14" />
                <path d="m12 5 7 7-7 7" />
              </svg>
            </div>

            <h3 className="font-serif text-xl text-ink-1 mb-2 group-hover:text-blue-600 transition-colors">
              {container.name}
            </h3>
            <p className="text-sm text-ink-2 mb-3 line-clamp-2">
              {container.theme || '—'}
            </p>
            {parentName && (
              <p className="text-[11px] uppercase tracking-[0.12em] text-ink-2/70 mb-2">
                Subcontainer of {parentName}
              </p>
            )}
            <p className="text-[11px] text-ink-2/80 font-mono break-all mb-4">
              ID {container.id}
            </p>

            <div className="mt-auto pt-4 border-t border-line-1/30 flex items-center justify-between text-xs text-ink-2 font-mono">
              <span>{container.stats?.document_count ?? 0} docs</span>
              <span>{container.stats?.chunk_count ?? 0} chunks</span>
            </div>

            <div className="absolute bottom-0 left-0 w-full h-1 bg-gradient-to-r from-blue-400/0 via-blue-400/40 to-purple-400/0 transform scale-x-0 group-hover:scale-x-100 transition-transform duration-500" />
          </GlassCard>
        </Link>
        <button
          type="button"
          onClick={() => openDeleteModal(container)}
          className="absolute top-3 right-3 inline-flex items-center justify-center rounded-full border border-line-2 bg-white/80 px-2.5 py-1.5 text-[11px] uppercase tracking-[0.12em] text-ink-2 opacity-0 transition group-hover:opacity-100 focus-visible:opacity-100 hover:text-ember hover:border-ember/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink-1/20"
          aria-label={`Delete ${container.name}`}
        >
          {container.state === 'archived' ? 'Delete' : 'Archive'}
        </button>
      </div>
    );
  };

  return (
    <GlassShell headline="Containers">
      <div className="space-y-8">
        <GlassCard className="col-span-full bg-gradient-to-r from-white/70 to-white/40 border border-white/40 shadow-glass" hoverEffect={false}>
          <div className="flex flex-col gap-4">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-ink-1">New container</p>
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
                  className="w-full rounded-xl border border-white/30 bg-white/90 px-3 py-2 text-sm text-ink-1 placeholder:text-ink-2/70 shadow-inner focus:outline-none focus:ring-2 focus:ring-blue-300/70"
                />
              </label>

              <label className="space-y-2">
                <span className="text-xs uppercase tracking-wide text-ink-2">Theme</span>
                <input
                  required
                  value={form.theme}
                  onChange={(e) => setForm((prev) => ({ ...prev, theme: e.target.value }))}
                  className="w-full rounded-xl border border-white/30 bg-white/90 px-3 py-2 text-sm text-ink-1 placeholder:text-ink-2/70 shadow-inner focus:outline-none focus:ring-2 focus:ring-blue-300/70"
                />
              </label>

              <label className="space-y-2">
                <span className="text-xs uppercase tracking-wide text-ink-2">Parent container</span>
                <select
                  value={form.parent_id}
                  onChange={(e) => setForm((prev) => ({ ...prev, parent_id: e.target.value }))}
                  className="w-full rounded-xl border border-white/30 bg-white/90 px-3 py-2 text-sm text-ink-1 shadow-inner focus:outline-none focus:ring-2 focus:ring-blue-300/70"
                >
                  <option value="">None (top-level)</option>
                  {parentOptions.map((container) => (
                    <option key={container.id} value={container.id}>
                      {container.name}
                    </option>
                  ))}
                </select>
              </label>

              <label className="space-y-2">
                <span className="text-xs uppercase tracking-wide text-ink-2">Embedder</span>
                <input
                  value={form.embedder}
                  onChange={(e) => setForm((prev) => ({ ...prev, embedder: e.target.value }))}
                  className="w-full rounded-xl border border-white/30 bg-white/90 px-3 py-2 text-sm text-ink-1 placeholder:text-ink-2/70 shadow-inner focus:outline-none focus:ring-2 focus:ring-blue-300/70"
                />
              </label>

              <label className="space-y-2 lg:col-span-2">
                <span className="text-xs uppercase tracking-wide text-ink-2">Description</span>
                <textarea
                  value={form.description}
                  onChange={(e) => setForm((prev) => ({ ...prev, description: e.target.value }))}
                  className="w-full rounded-xl border border-white/30 bg-white/90 px-3 py-2 text-sm text-ink-1 placeholder:text-ink-2/70 shadow-inner focus:outline-none focus:ring-2 focus:ring-blue-300/70 min-h-[64px]"
                />
              </label>

              <label className="space-y-2">
                <span className="text-xs uppercase tracking-wide text-ink-2">Mission context</span>
                <textarea
                  value={form.mission_context}
                  onChange={(e) => setForm((prev) => ({ ...prev, mission_context: e.target.value }))}
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
                        className={`px-3 py-2 rounded-full border text-xs cursor-pointer transition ${checked
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
                  Auto-refresh
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
        <div className="flex flex-wrap items-center gap-2 border-b border-line-1/50 pb-4">
          <button
            onClick={() => setStateFilter('active')}
            className={`px-4 py-2 rounded-full text-sm transition-all duration-300 ${stateFilter === 'active'
              ? 'bg-white text-ink-1 shadow-glass font-medium'
              : 'text-ink-2 hover:text-ink-1 hover:bg-white/40'
              }`}
          >
            Active
          </button>
          <button
            onClick={() => setStateFilter('all')}
            className={`px-4 py-2 rounded-full text-sm transition-all duration-300 ${stateFilter === 'all'
              ? 'bg-white text-ink-1 shadow-glass font-medium'
              : 'text-ink-2 hover:text-ink-1 hover:bg-white/40'
              }`}
          >
            All
          </button>
          {deleteSuccess && (
            <span className="ml-auto text-xs text-ink-1 bg-paper-0/80 border border-line-2 px-3 py-1 rounded-full">
              {deleteSuccess}
            </span>
          )}
          {deleteError && (
            <span className="ml-auto text-xs text-ember bg-amber-50 border border-amber-200 px-3 py-1 rounded-full">
              {deleteError}
            </span>
          )}
        </div>

        {/* Grid */}
        <div className="space-y-8">
          {isLoading && [1, 2, 3].map((i) => (
            <GlassCard key={i} className="h-48 animate-pulse bg-white/20 border-white/10">
              <div className="w-2/3 h-6 bg-white/20 rounded mb-4" />
              <div className="w-full h-4 bg-white/10 rounded mb-2" />
              <div className="w-1/2 h-4 bg-white/10 rounded" />
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

          {!isLoading && !isError && rootContainers.map((container) => {
            const children = (childrenByParent[container.id] || []).sort((a, b) =>
              a.name.localeCompare(b.name)
            );
            const hasChildren = children.length > 0;

            return (
              <div key={container.id} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {renderCard(container)}
                </div>
                {hasChildren && (
                  <div className="border-l border-line-2 pl-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {children.map((child) =>
                        renderCard(child, { compact: true, parentName: container.name })
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <AdminActionModal
        open={!!deleteTarget}
        title={deletePermanent ? 'Delete container permanently' : 'Archive container'}
        description={deleteTarget ? `Container "${deleteTarget.name}" will be ${deletePermanent ? 'removed' : 'archived'} from active views.` : undefined}
        onClose={() => {
          setDeleteTarget(null);
          setDeletePermanent(false);
          setDeleteError(null);
        }}
        onSubmit={handleDelete}
        submitLabel={deletePermanent ? 'Delete permanently' : 'Archive container'}
        busy={isDeleting}
        error={deleteError}
      >
        {deleteTarget && (
          <div className="space-y-3">
            <div className="rounded-xl border border-line-2 bg-paper-0/70 px-3 py-2 text-xs text-ink-2">
              <span className="font-medium text-ink-1">{deleteTarget.name}</span>
              <span className="mx-2 text-ink-2/50">·</span>
              <span>{deleteTarget.stats?.document_count ?? 0} docs</span>
              <span className="mx-2 text-ink-2/50">·</span>
              <span>{deleteTarget.stats?.chunk_count ?? 0} chunks</span>
            </div>
            <label className="flex items-center gap-2 text-sm text-ink-1">
              <input
                type="checkbox"
                checked={deletePermanent}
                onChange={(event) => setDeletePermanent(event.target.checked)}
                className="h-4 w-4 rounded border-line-2 text-ember focus:ring-ember/40"
              />
              Permanently delete
            </label>
          </div>
        )}
      </AdminActionModal>
    </GlassShell>
  );
}
