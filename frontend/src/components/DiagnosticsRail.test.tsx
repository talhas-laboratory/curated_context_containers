import { render, screen } from '@testing-library/react';
import { DiagnosticsRail } from './DiagnosticsRail';

describe('DiagnosticsRail', () => {
  it('shows diagnostics data when visible', () => {
    render(
      <DiagnosticsRail
        visible
        diagnostics={{
          mode: 'hybrid',
          bm25_hits: 1,
          vector_hits: 1,
          latency_budget_ms: 900,
          latency_over_budget_ms: 0,
        }}
        timings={{
          total_ms: 150,
          vector_ms: 80,
          bm25_ms: 40,
          fuse_ms: 30,
        }}
        goldenSummary={null}
      />
    );

    expect(screen.getByLabelText('Search diagnostics')).toBeVisible();
    expect(screen.getByText(/hybrid/)).toBeInTheDocument();
    expect(screen.getAllByText(/150 ms/).length).toBeGreaterThan(0);
  });

  it('is hidden when not visible', () => {
    render(<DiagnosticsRail visible={false} />);
    expect(screen.getByTestId('diagnostics-rail')).toHaveAttribute('aria-hidden', 'true');
  });
});
