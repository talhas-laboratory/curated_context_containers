import { defineConfig } from '@playwright/test';

const baseURL = process.env.FRONTEND_URL || 'http://localhost:3000';

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 60_000,
  retries: process.env.CI ? 1 : 0,
  use: {
    baseURL,
    headless: true,
    trace: 'retain-on-failure',
  },
  reporter: process.env.CI ? 'line' : 'list',
});
