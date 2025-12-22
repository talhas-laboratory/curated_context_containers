import { expect, test } from '@playwright/test';

const token =
  process.env.NEXT_PUBLIC_MCP_TOKEN || process.env.LLC_MCP_TOKEN || process.env.CI_MCP_TOKEN || 'local-dev-token';
const searchPath = process.env.FRONTEND_PATH || '/containers/expressionist-art/search';

test.describe('Graph search flow', () => {
  test('runs graph mode search and shows graph context', async ({ page }) => {
    test.skip(process.env.CI_E2E === '0', 'E2E disabled via CI_E2E=0');

    await page.addInitScript(([storedToken]) => {
      window.localStorage.setItem('llc_mcp_token', storedToken);
    }, [token]);

    await page.goto(searchPath, { waitUntil: 'networkidle' });

    const searchInput = page.getByTestId('search-input');
    await expect(searchInput).toBeVisible();

    await page.getByRole('button', { name: /^Graph$/ }).click();
    await searchInput.fill('graph query');
    await searchInput.press('Enter');

    const graphContext = page.getByTestId('graph-context');
    await expect(graphContext).toBeVisible({ timeout: 15000 });
    await expect(graphContext).toContainText('Graph context');
    await expect(graphContext).toContainText(/GraphOS|graph_ms/i);
  });
});
