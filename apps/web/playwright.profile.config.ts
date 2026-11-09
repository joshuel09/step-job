import { defineConfig, devices } from "@playwright/test";

/** Run the profile UI against an isolated API fixture, without a DB or model. */
export default defineConfig({
  testDir: "./tests/profile-browser",
  outputDir: "test-results/profile",
  fullyParallel: true,
  workers: 2,
  use: {
    baseURL: "http://localhost:3189",
    ...devices["Desktop Chrome"],
    channel: process.env.PLAYWRIGHT_CHANNEL,
  },
  webServer: [
    {
      command: "node tests/profile-browser/profile-mock-api.mjs",
      url: "http://127.0.0.1:8199/health",
    },
    {
      command:
        process.env.PROFILE_TEST_PRODUCTION === "1"
          ? "pnpm exec next build && pnpm exec next start --port 3189"
          : "pnpm exec next dev --port 3189",
      url: "http://localhost:3189/icon.svg",
      timeout: 120_000,
      env: {
        NEXT_PUBLIC_API_URL: "http://127.0.0.1:8199/api/v1",
        NEXT_PUBLIC_DEV_SESSION: "1",
        PROFILE_BROWSER_TEST: "1",
      },
    },
  ],
});
