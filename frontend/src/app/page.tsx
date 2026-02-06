'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useListContainers } from '../lib/hooks/use-containers';

/**
 * Home page - redirects to first active container or containers list
 */
export default function HomePage() {
  const router = useRouter();
  const { data, isLoading, error } = useListContainers('active');

  useEffect(() => {
    if (data && data.containers.length > 0) {
      // Redirect to first active container's search page
      router.replace(`/containers/${data.containers[0].id}/search`);
    } else if (data && data.containers.length === 0) {
      // No containers, go to containers list
      router.replace('/containers');
    }
  }, [data, router]);

  return (
    <main className="mx-auto flex max-w-6xl items-center justify-center px-6 py-20" aria-live="polite">
      <div className="text-center space-y-3">
        {isLoading && <p className="mt-2 text-sm text-chrome-500">Loading…</p>}
        {error && (
          <p className="mt-2 text-sm text-red-700" role="alert">
            Failed to load containers.
          </p>
        )}
      </div>
    </main>
  );
}
