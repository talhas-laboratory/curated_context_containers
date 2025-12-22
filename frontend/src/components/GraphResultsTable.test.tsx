import { render, screen } from '@testing-library/react';
import { GraphResultsTable } from './GraphResultsTable';

describe('GraphResultsTable', () => {
  const nodes = [
    { id: 'n1', label: 'GraphOS', type: 'Project', summary: 'Platform', source_chunk_ids: ['c1'] },
  ];
  const edges = [{ source: 'Team', target: 'GraphOS', type: 'WORKS_ON', source_chunk_ids: ['c2'] }];
  const snippets = [
    { chunk_id: 'c1', title: 'Decision doc', text: 'Context', uri: 'doc://1' },
    { chunk_id: 'c2', title: 'Team note', text: 'Relation', uri: 'doc://2' },
  ];

  it('renders nodes, edges, and snippets with provenance', () => {
    render(<GraphResultsTable nodes={nodes} edges={edges} snippets={snippets} maxHops={2} />);

    expect(screen.getByText('Graph context')).toBeInTheDocument();
    expect(screen.getAllByText('GraphOS')[0]).toBeInTheDocument();
    expect(screen.getByText('Team')).toBeInTheDocument();
    expect(screen.getAllByText(/Decision doc/)[0]).toBeInTheDocument();
    expect(screen.getAllByText(/Team note|Decision doc/).length).toBeGreaterThan(0);
  });

  it('hides when no data', () => {
    render(<GraphResultsTable nodes={[]} edges={[]} snippets={[]} />);
    expect(screen.queryByText('Graph context')).toBeNull();
  });
});
