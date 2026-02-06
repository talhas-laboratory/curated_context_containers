'use client';

import { FormEvent, RefObject } from 'react';

interface SearchInputProps {
  value: string;
  placeholder?: string;
  diagnosticsEnabled?: boolean;
  loading?: boolean;
  inputRef?: RefObject<HTMLInputElement>;
  className?: string;
  onChange?: (value: string) => void;
  onToggleDiagnostics?: () => void;
  onSubmit?: (value: string) => void;
}

export function SearchInput({
  value,
  placeholder = 'Search',
  diagnosticsEnabled = false,
  loading = false,
  inputRef,
  className = '',
  onChange,
  onToggleDiagnostics,
  onSubmit,
}: SearchInputProps) {
  const handleSubmit = (evt: FormEvent<HTMLFormElement>) => {
    evt.preventDefault();
    onSubmit?.(value);
  };

  return (
    <form onSubmit={handleSubmit} className={`space-y-3 ${className}`} aria-live="polite">
      <label className="sr-only" htmlFor="search-input">
        Query
      </label>
      <div className="flex items-center gap-3 rounded-full border border-line-2 bg-paper-1 px-5 py-3 focus-within:border-ink-1 focus-within:bg-paper-0 focus-within:ring-2 focus-within:ring-line-1 transition">
        <input
          type="text"
          id="search-input"
          ref={inputRef}
          value={value}
          placeholder={placeholder}
          onChange={(event) => onChange?.(event.target.value)}
          className="flex-1 border-none bg-transparent text-base text-ink-1 outline-none placeholder:text-ink-2"
          aria-label="Search query"
          aria-autocomplete="none"
          role="searchbox"
          aria-busy={loading}
          data-testid="search-input"
        />
        <button
          type="button"
          onClick={onToggleDiagnostics}
          aria-label="Toggle diagnostics"
          aria-pressed={diagnosticsEnabled}
          className={`rounded-full border px-3 py-1 text-xs uppercase tracking-[0.1em] transition ${
            diagnosticsEnabled
              ? 'border-ink-1 text-ink-1'
              : 'border-line-2 text-ink-2 hover:border-ink-1 hover:text-ink-1'
          }`}
          data-testid="diagnostics-toggle"
        >
          Diagnostics
        </button>
        <button
          type="submit"
          disabled={loading}
          className="rounded-full border border-ink-1 px-5 py-2 text-sm font-medium text-ink-1 transition hover:bg-ink-1 hover:text-paper-1 disabled:cursor-not-allowed disabled:border-line-2 disabled:text-line-2"
          aria-busy={loading}
          data-testid="search-submit"
        >
          {loading ? 'Searching…' : 'Search'}
        </button>
      </div>
    </form>
  );
}
