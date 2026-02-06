import { act, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { vi } from 'vitest';

import ChatSandboxPage from './page';
import { server } from '../../tests/msw/server';
import { renderWithQueryClient } from '../../tests/utils';

vi.mock('next/navigation', () => ({
  usePathname: () => '/chat-sandbox',
}));

describe('ChatSandboxPage', () => {
  it('uploads PDFs via /sandbox/upload (not /api/sandbox/upload)', async () => {
    const user = userEvent.setup();
    let uploadUrl: string | null = null;

    server.use(
      http.post('*/sandbox/upload', async ({ request }) => {
        uploadUrl = request.url;
        return HttpResponse.json({
          uri: 'https://example.com/sandbox/test.pdf',
          filename: 'test.pdf',
          key: 'test-key',
        });
      })
    );

    renderWithQueryClient(<ChatSandboxPage />);

    // Wait for containers to load (MSW fixture)
    await screen.findByText('Expressionist Art');

    const input = document.querySelector('input[type="file"]') as HTMLInputElement | null;
    expect(input).toBeTruthy();

    const file = new File(['%PDF-1.4'], 'test.pdf', { type: 'application/pdf' });
    await act(async () => {
      await user.upload(input!, file);
    });

    await screen.findByText(/Queued \"test\.pdf\"\./i);
    expect(uploadUrl).toContain('/sandbox/upload');
    expect(uploadUrl).not.toContain('/api/sandbox/upload');
  });

  it("blocks PDF uploads into containers that don't accept PDFs", async () => {
    const user = userEvent.setup();
    let uploadCount = 0;

    server.use(
      http.post('*/sandbox/upload', async () => {
        uploadCount += 1;
        return HttpResponse.json({
          uri: 'https://example.com/sandbox/test.pdf',
          filename: 'test.pdf',
          key: 'test-key',
        });
      })
    );

    renderWithQueryClient(<ChatSandboxPage />);
    await screen.findByText('Expressionist Art');

    // Select the text-only subcontainer fixture
    await act(async () => {
      await user.click(screen.getByRole('button', { name: /Expressionist Sketches/i }));
    });

    const uploadButton = document.querySelector('button[title="Upload PDF"]') as HTMLButtonElement | null;
    expect(uploadButton).toBeTruthy();
    expect(uploadButton).toBeDisabled();
    expect(uploadCount).toBe(0);
  });
});
