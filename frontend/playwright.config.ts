import { defineConfig, devices } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { loadE2EEnv } from "./e2e/fixtures/env";

const rootDir = path.dirname(fileURLToPath(import.meta.url));
const env = loadE2EEnv();

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  // Refresh tokens rotate per login; keep a single worker so fixtures never share sessions.
  workers: 1,
  timeout: 120_000,
  expect: { timeout: 20_000 },
  reporter: [["list"], ["html", { open: "never", outputFolder: "playwright-report" }]],
  globalSetup: path.join(rootDir, "e2e/global-setup.ts"),
  outputDir: "test-results",
  use: {
    baseURL: env.frontendUrl,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command: "npm run dev -- --host 127.0.0.1 --port 5175 --strictPort",
    url: "http://127.0.0.1:5175",
    reuseExistingServer: !process.env.CI,
    timeout: 180_000,
  },
});
