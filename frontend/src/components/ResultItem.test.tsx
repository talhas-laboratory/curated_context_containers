import { fireEvent, render, screen } from '@testing-library/react';
import { vi } from 'vitest';
import { ResultItem } from './ResultItem';
import type { SearchResult } from '../lib/types';

const baseResult: SearchResult = {
  chunk_id: 'chunk-1',
  doc_id: 'doc-1',
  container_id: 'container-1',
  container_name: 'Expressionist Art',
  title: 'History',
  snippet: 'Expressionism is a modernist movement...',
  score: 0.9,
  provenance: { source: 'wiki', ingested_at: '2024-01-01T00:00:00Z' },
  meta: { tags: ['art'] },
};

describe('ResultItem', () => {
  it('renders details and triggers selection on click and key', () => {
    const onSelect = vi.fn();
    render(<ResultItem result={baseResult} onSelect={onSelect} diagnosticsVisible selected />);

    expect(screen.getByText('Expressionist Art')).toBeInTheDocument();
    expect(screen.getByText('0.9')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('result-item'));
    expect(onSelect).toHaveBeenCalledWith(baseResult);

    fireEvent.keyDown(screen.getByTestId('result-item'), { key: 'Enter' });
    expect(onSelect).toHaveBeenCalledTimes(2);
  });
});
