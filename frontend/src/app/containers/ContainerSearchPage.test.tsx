import { act, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import ContainerSearchPage from './[id]/search/page';
import { renderWithQueryClient } from '../../tests/utils';

vi.mock('next/navigation', () => ({
  useParams: () => ({ id: 'container-1' }),
  useRouter: () => ({ replace: vi.fn() }),
  usePathname: () => '/containers/container-1/search',
}));

describe('ContainerSearchPage', () => {
  it('loads container data and returns search results', async () => {
    const user = userEvent.setup();
    renderWithQueryClient(<ContainerSearchPage />);

    await screen.findByText('Expressionist Art');
    await screen.findByText('History of Expressionism');
    const input = screen.getByTestId('search-input');
    await act(async () => {
      await user.clear(input);
      await user.type(input, 'smoke');
      await user.click(screen.getByTestId('search-submit'));
    });

    const results = await screen.findAllByTestId('result-item');
    expect(results.length).toBeGreaterThan(0);
    expect(screen.queryByTestId('search-error')).not.toBeInTheDocument();
  });

  it('shows empty state when no hits returned', async () => {
    const user = userEvent.setup();
    renderWithQueryClient(<ContainerSearchPage />);

    await screen.findByText('Expressionist Art');
    const input = screen.getByTestId('search-input');
    await act(async () => {
      await user.clear(input);
      await user.type(input, 'empty');
      await user.click(screen.getByTestId('search-submit'));
    });

    const status = await screen.findByTestId('search-status');
    expect(status).toHaveTextContent('No hits');
  });

  it('allows deleting a document from the sidebar panel', async () => {
    const user = userEvent.setup();
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);

    renderWithQueryClient(<ContainerSearchPage />);

    await screen.findByText('History of Expressionism');
    const removeButton = screen.getByRole('button', { name: /remove/i });
    await act(async () => {
      await user.click(removeButton);
    });

    await screen.findByText('No documents found.');

    confirmSpy.mockRestore();
  });
});
