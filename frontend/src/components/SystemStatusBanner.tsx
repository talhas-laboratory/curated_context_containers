'use client';

import { useMemo } from 'react';

import { useSystemStatus } from '../lib/hooks/use-system-status';
import type { MCPError } from '../lib/mcp-client';

function titleCase(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

export function SystemStatusBanner() {
  const { data, error, isLoading } = useSystemStatus();

  const degradedServices = useMemo(() => {
    if (!data?.checks) return [];
    return Object.entries(data.checks)
      .filter(([, ok]) => !ok)
      .map(([name]) => name);
  }, [data]);

  const degradedErrorLines = useMemo(() => {
    if (!data?.errors) return [];
    return degradedServices
      .map((name) => {
        const msg = data.errors?.[name];
        return msg ? `${titleCase(name)}: ${msg}` : null;
      })
      .filter((line): line is string => Boolean(line));
  }, [data, degradedServices]);

  if (isLoading) return null;

  // If the backend is unreachable, show a clear banner (local dev friendliness).
  if (error) {
    const err = error as unknown as Partial<MCPError>;
    if (err?.status === 401) {
      return (
        <div className="mb-6 rounded-2xl border border-amber-200 bg-amber-50/70 px-4 py-3 text-sm text-amber-900">
          <div className="font-medium">Authentication required</div>
          <div className="mt-1 text-amber-900/80">
            The MCP API rejected your request. Set a bearer token (for example: <span className="font-mono">NEXT_PUBLIC_MCP_TOKEN</span>)
            and refresh.
          </div>
        </div>
      );
    }
    return (
      <div className="mb-6 rounded-2xl border border-red-200 bg-red-50/70 px-4 py-3 text-sm text-red-800">
        <div className="font-medium">Backend unreachable</div>
        <div className="mt-1 text-red-700/80">
          The MCP API did not respond. If you just started the stack, wait a moment and refresh.
        </div>
      </div>
    );
  }

  if (!data || data.status === 'ok') return null;

  const servicesText = degradedServices.length ? degradedServices.map(titleCase).join(', ') : 'Unknown';

  return (
    <div className="mb-6 rounded-2xl border border-amber-200 bg-amber-50/70 px-4 py-3 text-sm text-amber-900">
      <div className="font-medium">System degraded</div>
      <div className="mt-1 text-amber-900/80">
        Some services are unavailable: <span className="font-mono">{servicesText}</span>. Search and ingestion may be
        partially unavailable.
      </div>
      {degradedErrorLines.length ? (
        <details className="mt-2">
          <summary className="cursor-pointer select-none text-amber-900/80">Details</summary>
          <pre className="mt-2 overflow-auto rounded-xl bg-amber-100/60 p-3 text-xs leading-relaxed text-amber-950">
            {degradedErrorLines.join('\n')}
          </pre>
        </details>
      ) : null}
    </div>
  );
}
