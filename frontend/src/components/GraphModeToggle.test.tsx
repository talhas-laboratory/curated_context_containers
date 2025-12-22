import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import { GraphModeToggle } from './GraphModeToggle';

describe('GraphModeToggle', () => {
  it('renders options and toggles selection', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <GraphModeToggle
        options={[
          { label: 'Hybrid', value: 'hybrid' },
          { label: 'Graph', value: 'graph' },
        ]}
        value="hybrid"
        onChange={onChange}
      />
    );

    expect(screen.getByRole('group', { name: /search mode/i })).toBeInTheDocument();
    const graphButton = screen.getByRole('button', { name: 'Graph' });
    expect(graphButton).toHaveAttribute('aria-pressed', 'false');

    await user.click(graphButton);
    expect(onChange).toHaveBeenCalledWith('graph');
  });
});
