import { act, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { vi } from 'vitest';
import { server } from '../../tests/msw/server';
import { renderWithQueryClient } from '../../tests/utils';
import ContainersPage from './page';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => '/containers',
}));

const parentContainer = {
  id: 'parent-1',
  name: 'Parent Container',
  theme: 'Primary',
  modalities: ['text'],
  state: 'active',
  parent_id: null,
  stats: { document_count: 1, chunk_count: 2 },
};

const childContainer = {
  id: 'child-1',
  name: 'Child Container',
  theme: 'Secondary',
  modalities: ['text'],
  state: 'active',
  parent_id: 'parent-1',
  stats: { document_count: 0, chunk_count: 0 },
};

describe('ContainersPage', () => {
  it('renders parent and subcontainers with hierarchy labels', async () => {
    server.use(
      http.post('*/v1/containers/list', () =>
        HttpResponse.json({ containers: [parentContainer, childContainer], total: 2 })
      )
    );

    renderWithQueryClient(<ContainersPage />);

    await screen.findByRole('heading', { name: 'Parent Container' });
    await screen.findByRole('heading', { name: 'Child Container' });
    expect(screen.getByText('Subcontainer of Parent Container')).toBeInTheDocument();
  });

  it('submits parent_id when creating a subcontainer', async () => {
    const user = userEvent.setup();
    let received: any = null;

    server.use(
      http.post('*/v1/containers/list', () =>
        HttpResponse.json({ containers: [parentContainer], total: 1 })
      ),
      http.post('*/v1/containers/create', async ({ request }) => {
        received = await request.json();
        return HttpResponse.json({
          version: 'v1',
          request_id: 'req-create',
          success: true,
          container_id: 'child-new',
          message: 'Container created',
        });
      })
    );

    renderWithQueryClient(<ContainersPage />);

    await screen.findByRole('heading', { name: 'Parent Container' });

    await act(async () => {
      await user.type(screen.getByLabelText('Name'), 'child-new');
      await user.type(screen.getByLabelText('Theme'), 'Child theme');
      await user.selectOptions(screen.getByLabelText('Parent container'), 'parent-1');
      await user.click(screen.getByRole('button', { name: /create container/i }));
    });

    expect(received?.parent_id).toBe('parent-1');
  });
});
