import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import { SearchInput } from './SearchInput';

describe('SearchInput', () => {
  it('submits query and toggles diagnostics', async () => {
    const onSubmit = vi.fn();
    const onToggleDiagnostics = vi.fn();
    const user = userEvent.setup();

    render(
      <SearchInput
        value="smoke"
        diagnosticsEnabled={false}
        onSubmit={onSubmit}
        onToggleDiagnostics={onToggleDiagnostics}
      />
    );

    await user.click(screen.getByTestId('search-submit'));
    expect(onSubmit).toHaveBeenCalledWith('smoke');

    await user.click(screen.getByTestId('diagnostics-toggle'));
    expect(onToggleDiagnostics).toHaveBeenCalled();
  });

  it('shows loading state', () => {
    render(<SearchInput value="loading" loading />);
    expect(screen.getByTestId('search-submit')).toHaveAttribute('aria-busy', 'true');
    expect(screen.getByTestId('search-submit')).toBeDisabled();
  });
});
