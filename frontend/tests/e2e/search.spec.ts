import { expect, test } from '@playwright/test';

const token =
  process.env.NEXT_PUBLIC_MCP_TOKEN || process.env.LLC_MCP_TOKEN || process.env.CI_MCP_TOKEN || 'local-dev-token';
const searchPath = process.env.FRONTEND_PATH || '/containers/expressionist-art/search';

test.describe('Search flow', () => {
  test('runs search and opens/closes modal', async ({ page }) => {
    test.skip(process.env.CI_E2E === '0', 'E2E disabled via CI_E2E=0');

    await page.addInitScript(([storedToken]) => {
      window.localStorage.setItem('llc_mcp_token', storedToken);
    }, [token]);

    await page.goto(searchPath, { waitUntil: 'networkidle' });

    const searchInput = page.getByTestId('search-input');
    await expect(searchInput).toBeVisible();
    await searchInput.fill('smoke');
    await searchInput.press('Enter');

    const firstResult = page.getByTestId('result-item').first();
    await expect(firstResult).toBeVisible({ timeout: 15000 });
    await firstResult.click();

    await expect(page.getByTestId('document-modal')).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(page.getByTestId('document-modal')).toBeHidden();
  });
});
