'use client';

import { useEffect, useRef } from 'react';
import { createFocusTrap } from '../lib/keyboard';
import { getMotionProps } from '../lib/motion';
import type { SearchResult } from '../lib/types';

interface DocumentModalProps {
  result: SearchResult | null;
  isOpen: boolean;
  onClose: () => void;
}

export function DocumentModal({ result, isOpen, onClose }: DocumentModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen || !modalRef.current) {
      return;
    }

    // Focus trap
    const cleanup = createFocusTrap(modalRef.current);

    // Handle Escape key
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);

    // Prevent body scroll
    document.body.style.overflow = 'hidden';

    return () => {
      cleanup();
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = '';
    };
  }, [isOpen, onClose]);

  if (!isOpen || !result) {
    return null;
  }

  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === overlayRef.current) {
      onClose();
    }
  };

  const formatMinIOUri = (uri?: string) => {
    if (!uri) return null;
    if (uri.startsWith('s3://')) {
      return uri;
    }
    return uri;
  };

  const minIOUri = formatMinIOUri(result.uri);
  const ingestedAt = result.provenance?.ingested_at;
  const ingestedAtLabel =
    typeof ingestedAt === 'string' || typeof ingestedAt === 'number'
      ? new Date(ingestedAt).toLocaleString()
      : null;

  return (
    <div
      ref={overlayRef}
      onClick={handleOverlayClick}
      className="fixed inset-0 z-50 flex items-center justify-center bg-paper-0/95 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      aria-describedby="modal-description"
      data-testid="document-modal-overlay"
      {...getMotionProps(280, 'cubic-bezier(.34, 1.56, .64, 1)')}
    >
      <div
        ref={modalRef}
        className="relative max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-2xl border border-ink-1 bg-paper-1 p-8 shadow-lg"
        data-testid="document-modal"
      >
        <button
          onClick={onClose}
          className="absolute right-4 top-4 rounded-full p-2 text-chrome-400 hover:bg-chrome-100 hover:text-chrome-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-chrome-900"
          aria-label="Close modal"
        >
          <svg
            className="h-5 w-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>

        <header className="mb-6">
          <h2 id="modal-title" className="text-2xl font-light text-ink-1">
            {result.title || 'Untitled Document'}
          </h2>
          <p className="mt-2 text-sm text-ink-2">
            {result.container_name || result.container_id}
          </p>
        </header>

        <div id="modal-description" className="space-y-6">
          <section>
            <h3 className="mb-2 text-sm font-medium uppercase tracking-wide text-chrome-400">
              Content
            </h3>
            <p className="text-base leading-relaxed text-ink-1">{result.snippet || 'No content available'}</p>
          </section>

          <section>
            <h3 className="mb-2 text-sm font-medium uppercase tracking-wide text-chrome-400">
              Provenance
            </h3>
            <dl className="space-y-2 text-sm">
              {result.provenance?.source && (
                <div>
                  <dt className="text-ink-2">Source</dt>
                  <dd className="text-ink-1">{String(result.provenance.source)}</dd>
                </div>
              )}
              {ingestedAtLabel && (
                <div>
                  <dt className="text-ink-2">Ingested</dt>
                  <dd className="text-ink-1">
                    {ingestedAtLabel}
                  </dd>
                </div>
              )}
              {result.modality && (
                <div>
                  <dt className="text-ink-2">Modality</dt>
                  <dd className="text-ink-1">{result.modality}</dd>
                </div>
              )}
              {result.provenance?.page && (
                <div>
                  <dt className="text-chrome-400">Page</dt>
                  <dd className="text-chrome-900">{String(result.provenance.page)}</dd>
                </div>
              )}
            </dl>
          </section>

          {minIOUri && (
            <section>
              <h3 className="mb-2 text-sm font-medium uppercase tracking-wide text-chrome-400">
                Storage URI
              </h3>
              <code className="block rounded border border-line-1 bg-paper-0 p-3 text-sm text-ink-1">
                {minIOUri}
              </code>
              <button
                onClick={() => {
                  navigator.clipboard.writeText(minIOUri);
                }}
                className="mt-2 text-sm text-chrome-600 hover:text-chrome-900"
              >
                Copy URI
              </button>
            </section>
          )}

          {result.meta && Object.keys(result.meta).length > 0 && (
            <section>
              <h3 className="mb-2 text-sm font-medium uppercase tracking-wide text-ink-2">
                Metadata
              </h3>
              <dl className="space-y-2 text-sm">
                {Object.entries(result.meta).map(([key, value]) => (
                  <div key={key}>
                    <dt className="text-ink-2">{key}</dt>
                    <dd className="text-ink-1">
                      {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                    </dd>
                  </div>
                ))}
              </dl>
            </section>
          )}

          {result.score !== undefined && (
            <section>
              <h3 className="mb-2 text-sm font-medium uppercase tracking-wide text-ink-2">
                Score
              </h3>
              <p className="text-lg font-semibold text-ink-1">{result.score.toFixed(3)}</p>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}
