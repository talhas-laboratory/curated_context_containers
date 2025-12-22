'use client';

import { useEffect, useRef, type FormEvent, type ReactNode } from 'react';

import { createFocusTrap } from '../lib/keyboard';

interface AdminActionModalProps {
  open: boolean;
  title: string;
  description?: string;
  onClose: () => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  submitLabel: string;
  busy?: boolean;
  error?: string | null;
  children: ReactNode;
}

export function AdminActionModal({
  open,
  title,
  description,
  onClose,
  onSubmit,
  submitLabel,
  busy = false,
  error = null,
  children,
}: AdminActionModalProps) {
  const overlayRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open || !containerRef.current) return;

    const cleanup = createFocusTrap(containerRef.current);
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    document.body.style.overflow = 'hidden';

    return () => {
      cleanup();
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [open, onClose]);

  if (!open) return null;

  const handleOverlayClick = (event: React.MouseEvent<HTMLDivElement>) => {
    if (event.target === overlayRef.current) {
      onClose();
    }
  };

  return (
    <div
      ref={overlayRef}
      onClick={handleOverlayClick}
      className="fixed inset-0 z-50 flex items-center justify-center bg-paper-0/90 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="admin-modal-title"
      data-testid="admin-modal"
    >
      <div
        ref={containerRef}
        className="w-full max-w-lg rounded-2xl border border-line-2 bg-white p-6 shadow-lg"
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.08em] text-ink-2">Maintenance</p>
            <h2 id="admin-modal-title" className="text-xl font-serif text-ink-1">
              {title}
            </h2>
            {description && <p className="mt-1 text-sm text-ink-2">{description}</p>}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-2 text-ink-2 hover:text-ink-1 hover:bg-paper-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink-1/30"
            aria-label="Close"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <form className="mt-4 space-y-4" onSubmit={onSubmit}>
          <div className="space-y-3 text-sm text-ink-1">{children}</div>

          {error && <p className="text-xs text-ember" role="alert">{error}</p>}

          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-full border border-line-2 px-3 py-2 text-sm text-ink-2 hover:border-ink-1 hover:text-ink-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink-1/30"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={busy}
              className="inline-flex items-center gap-2 rounded-full border border-ink-1 bg-ink-1 px-4 py-2 text-sm uppercase tracking-[0.08em] text-white transition hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink-1/40 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {busy && <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/50 border-t-white" aria-hidden />}
              {submitLabel}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
