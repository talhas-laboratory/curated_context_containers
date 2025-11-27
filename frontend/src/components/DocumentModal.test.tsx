import { fireEvent, render, screen } from '@testing-library/react';
import { vi } from 'vitest';
import { DocumentModal } from './DocumentModal';
import type { SearchResult } from '../lib/types';

const result: SearchResult = {
  chunk_id: 'chunk-1',
  doc_id: 'doc-1',
  container_id: 'container-1',
  container_name: 'Expressionist Art',
  title: 'History of Expressionism',
  snippet: 'Expressionism is a modernist movement...',
  score: 0.9,
  provenance: { source: 'wiki', ingested_at: '2024-01-01T00:00:00Z' },
  meta: { tags: ['art'] },
};

describe('DocumentModal', () => {
  it('does not render when closed', () => {
    render(<DocumentModal result={result} isOpen={false} onClose={vi.fn()} />);
    expect(screen.queryByTestId('document-modal')).not.toBeInTheDocument();
  });

  it('renders details when open and can close via overlay and escape', () => {
    const onClose = vi.fn();
    render(<DocumentModal result={result} isOpen onClose={onClose} />);

    expect(screen.getByTestId('document-modal')).toBeInTheDocument();
    fireEvent.click(screen.getByTestId('document-modal-overlay'));
    expect(onClose).toHaveBeenCalledTimes(1);

    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onClose).toHaveBeenCalledTimes(2);
  });
});
