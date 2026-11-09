import { defineConfig, devices } from "@playwright/test";

/** Run the translation UI against an isolated API fixture, without a DB or model. */
export default defineConfig({
  testDir: "./tests/translation-browser",
  testMatch: "translations.spec.ts",
  outputDir: "test-results/translations",
  fullyParallel: true,
  workers: 2,
  use: {
    baseURL: "http://localhost:3189",
    ...devices["Desktop Chrome"],
    channel: process.env.PLAYWRIGHT_CHANNEL,
  },
  webServer: [
    {
      command: "node tests/translation-browser/translation-mock-api.mjs",
      url: "http://127.0.0.1:8199/health",
    },
    {
      command: "pnpm exec next dev --port 3189",
      url: "http://localhost:3189/icon.svg",
      timeout: 120_000,
      env: { NEXT_PUBLIC_API_URL: "http://127.0.0.1:8199/api/v1", NEXT_PUBLIC_DEV_SESSION: "1" },
    },
  ],
});
