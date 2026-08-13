import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  testMatch: "presentation-m33.spec.ts",
  fullyParallel: false,
  workers: 1,
  timeout: 120_000,
  expect: { timeout: 20_000 },
  outputDir: "../../output/playwright/presentation-results",
  reporter: [["list"]],
  use: {
    baseURL: "http://127.0.0.1:4180",
    colorScheme: "dark",
    locale: "zh-CN",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "presentation-1280",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 720 } },
    },
    {
      name: "presentation-1080p",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1920, height: 1080 } },
    },
    {
      name: "presentation-2k",
      use: { ...devices["Desktop Chrome"], viewport: { width: 2560, height: 1440 } },
    },
    {
      name: "presentation-4k",
      use: { ...devices["Desktop Chrome"], viewport: { width: 3840, height: 2160 } },
    },
  ],
  webServer: [
    {
      command:
        "POLICYSCOPE_RUN_MODE=fake PYTHONPATH=.:apps/api/src .venv/bin/uvicorn policyscope_api.main:app --app-dir apps/api/src --port 8000",
      cwd: "../..",
      url: "http://127.0.0.1:8000/api/health",
      reuseExistingServer: true,
      timeout: 120_000,
    },
    {
      command: "npm run dev -- --host 127.0.0.1 --port 4180",
      cwd: "../presentation",
      url: "http://127.0.0.1:4180",
      reuseExistingServer: true,
      timeout: 120_000,
    },
  ],
});
