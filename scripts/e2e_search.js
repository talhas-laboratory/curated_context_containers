#!/usr/bin/env node
/**
 * Minimal E2E script for the search UI using Playwright.
 * Requires Playwright installed in frontend/node_modules (`cd frontend && npm install && npx playwright install`).
 */
const path = require("path");
const fs = require("fs");

if (process.env.CI_E2E === "0") {
  console.log("CI_E2E=0, skipping E2E search script");
  process.exit(0);
}

const FRONTEND_URL =
  process.env.FRONTEND_URL ||
  "http://localhost:3000/containers/expressionist-art/search";
const TOKEN =
  process.env.NEXT_PUBLIC_MCP_TOKEN ||
  process.env.LLC_MCP_TOKEN ||
  "local-dev-token";

async function main() {
  const { chromium } = require(path.join(
    __dirname,
    "..",
    "frontend",
    "node_modules",
    "playwright"
  ));

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();
  page.setDefaultTimeout(15000);

  const tracePath = path.join(__dirname, "..", ".artifacts", "e2e-trace.zip");
  fs.mkdirSync(path.dirname(tracePath), { recursive: true });
  await context.tracing.start({ screenshots: true, snapshots: true });

  await page.goto(FRONTEND_URL, { waitUntil: "networkidle" });
  await page.evaluate((token) => {
    localStorage.setItem("llc_mcp_token", token);
  }, TOKEN);
  await page.goto(FRONTEND_URL, { waitUntil: "networkidle" });

  const searchInput = await page
    .getByRole("textbox")
    .first()
    .catch(() => null);
  if (!searchInput) {
    await context.tracing.stop({ path: tracePath });
    await browser.close();
    throw new Error("Search input not found");
  }

  await searchInput.fill("smoke");
  await searchInput.press("Enter");
  await page.waitForTimeout(500);

  const resultSelector = "[data-testid='result-item'], article, li";
  await page.waitForSelector(resultSelector, { timeout: 10000 });
  const firstResult = await page.$(resultSelector);
  if (!firstResult) {
    await context.tracing.stop({ path: tracePath });
    await browser.close();
    throw new Error("No results found to open");
  }

  await firstResult.click();
  await page.waitForSelector("[role='dialog'], [data-testid='modal']", {
    timeout: 5000,
  });

  console.log("E2E search flow succeeded:", FRONTEND_URL);
  await context.tracing.stop({ path: tracePath });
  await browser.close();
}

main().catch((err) => {
  console.error("E2E search failed:", err);
  // Best-effort trace stop if something exploded before explicit stop.
  try {
    const tracePath = path.join(__dirname, "..", ".artifacts", "e2e-trace.zip");
    if (fs.existsSync(tracePath)) {
      console.error(`Trace captured at ${tracePath}`);
    }
  } catch {
    // ignore
  }
  process.exit(1);
});
