import { screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, it, expect } from 'vitest';

import { server } from '../tests/msw/server';
import { renderWithQueryClient } from '../tests/utils';
import { SystemStatusBanner } from './SystemStatusBanner';

describe('SystemStatusBanner', () => {
  it('shows degraded banner when checks fail', async () => {
    server.use(
      http.get('*/v1/system/status', async () => {
        return HttpResponse.json({
          version: 'v1',
          request_id: 'req-system',
          status: 'degraded',
          required_ok: true,
          checks: { postgres: true, qdrant: false, minio: true, neo4j: true },
          errors: { qdrant: 'down' },
          migrations: null,
          issues: ['QDRANT_DOWN'],
        });
      })
    );

    renderWithQueryClient(<SystemStatusBanner />);

    expect(await screen.findByText(/System degraded/i)).toBeInTheDocument();
    expect(screen.getByText('Qdrant', { selector: 'span' })).toBeInTheDocument();
  });

  it('shows unreachable banner when API errors', async () => {
    server.use(
      http.get('*/v1/system/status', async () => {
        return HttpResponse.error();
      })
    );

    renderWithQueryClient(<SystemStatusBanner />);

    expect(await screen.findByText(/Backend unreachable/i)).toBeInTheDocument();
  });

  it('shows auth banner when API returns 401', async () => {
    server.use(
      http.get('*/v1/system/status', async () => {
        return HttpResponse.json(
          { error: { code: 'AUTH_FAILED', message: 'Auth failed' } },
          { status: 401 }
        );
      })
    );

    renderWithQueryClient(<SystemStatusBanner />);

    expect(await screen.findByText(/Authentication required/i)).toBeInTheDocument();
  });
});
