'use client';

import { useRouter } from 'next/navigation';
import type { ContainerSummary } from '../lib/types';

interface ContainerCardProps {
  container: ContainerSummary;
}

export function ContainerCard({ container }: ContainerCardProps) {
  const router = useRouter();

  const handleClick = () => {
    router.push(`/containers/${container.id}/search`);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleClick();
    }
  };

  return (
    <article
      role="button"
      tabIndex={0}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      className="group cursor-pointer rounded-2xl border border-chrome-200 bg-white p-10 shadow-sm transition-all hover:-translate-y-0.5 hover:border-chrome-400 hover:shadow-md focus:outline-none focus-visible:ring-2 focus-visible:ring-chrome-900"
      aria-label={`${container.name} container, ${container.stats?.document_count || 0} documents`}
    >
      <div className="space-y-4">
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <h3 className="text-xl font-light text-chrome-900">{container.name}</h3>
            <p className="text-sm text-chrome-500">{container.theme}</p>
          </div>
          <span
            className={`rounded-full px-3 py-1 text-xs font-medium uppercase tracking-wide ${
              container.state === 'active'
                ? 'bg-chrome-100 text-chrome-700'
                : container.state === 'paused'
                ? 'bg-yellow-100 text-yellow-700'
                : 'bg-chrome-200 text-chrome-500'
            }`}
          >
            {container.state}
          </span>
        </div>

        <div className="flex flex-wrap gap-2">
          {container.modalities.map((modality) => (
            <span
              key={modality}
              className="rounded-full bg-chrome-50 px-2 py-1 text-xs uppercase tracking-wide text-chrome-600"
            >
              {modality}
            </span>
          ))}
        </div>

        {container.stats && (
          <dl className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <dt className="text-chrome-400">Documents</dt>
              <dd className="font-semibold text-chrome-900">{container.stats.document_count || 0}</dd>
            </div>
            <div>
              <dt className="text-chrome-400">Chunks</dt>
              <dd className="font-semibold text-chrome-900">{container.stats.chunk_count || 0}</dd>
            </div>
            {container.stats.last_ingest && (
              <div className="col-span-2">
                <dt className="text-chrome-400">Last ingest</dt>
                <dd className="text-chrome-600">
                  {new Date(container.stats.last_ingest).toLocaleDateString()}
                </dd>
              </div>
            )}
          </dl>
        )}
      </div>
    </article>
  );
}

