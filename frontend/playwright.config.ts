import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end tests across both applications.
 *
 * Uses the installed Google Chrome rather than Playwright's bundled Chromium:
 * this machine runs macOS 12, which the bundled build no longer supports.
 * `channel: "chrome"` drives the real browser instead.
 *
 * Both servers must already be running:
 *   Django  http://127.0.0.1:8000
 *   Next    http://localhost:3000
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  timeout: 45_000,
  expect: { timeout: 10_000 },

  use: {
    baseURL: "http://localhost:3000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    // Slow enough to follow along in headed mode without being tedious.
    launchOptions: { slowMo: process.env.HEADED ? 400 : 0 },
  },

  projects: [
    {
      name: "chrome",
      use: { ...devices["Desktop Chrome"], channel: "chrome" },
    },
  ],
});
