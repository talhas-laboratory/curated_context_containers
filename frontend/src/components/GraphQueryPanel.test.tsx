import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import { GraphQueryPanel } from './GraphQueryPanel';

describe('GraphQueryPanel', () => {
  it('toggles raw Cypher and submits with hotkey', async () => {
    const user = userEvent.setup();
    const onToggle = vi.fn();
    const onChange = vi.fn();
    const onSubmit = vi.fn();

    render(
      <GraphQueryPanel
        mode="graph"
        rawCypherEnabled={false}
        rawCypher=""
        onToggleRawCypher={onToggle}
        onChangeRawCypher={onChange}
        onSubmit={onSubmit}
      />
    );

    await user.click(screen.getByLabelText(/raw cypher/i));
    expect(onToggle).toHaveBeenCalledWith(true);
  });

  it('renders textarea when enabled and handles shortcuts', async () => {
    const user = userEvent.setup();
    const onToggle = vi.fn();
    const onChange = vi.fn();
    const onSubmit = vi.fn();

    render(
      <GraphQueryPanel
        mode="graph"
        rawCypherEnabled
        rawCypher="MATCH (n) RETURN n"
        onToggleRawCypher={onToggle}
        onChangeRawCypher={onChange}
        onSubmit={onSubmit}
      />
    );

    const textarea = screen.getByLabelText(/raw cypher input/i);
    await user.type(textarea, ' ');
    expect(onChange).toHaveBeenCalled();

    await user.keyboard('{Meta>}{Enter}{/Meta}');
    expect(onSubmit).toHaveBeenCalled();

    await user.keyboard('{Escape}');
    expect(onToggle).toHaveBeenCalledWith(false);
  });
});
