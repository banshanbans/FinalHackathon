import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  testMatch: "readme-capture.spec.ts",
  fullyParallel: false,
  workers: 1,
  timeout: 120_000,
  expect: { timeout: 20_000 },
  outputDir: "../../output/playwright/readme-results",
  reporter: [["list"]],
  use: {
    ...devices["Desktop Chrome"],
    baseURL: "http://127.0.0.1:4182",
    colorScheme: "dark",
    locale: "zh-CN",
    reducedMotion: "reduce",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    viewport: { width: 1600, height: 900 },
  },
  webServer: [
    {
      command:
        "POLICYSCOPE_RUN_MODE=fake PYTHONPATH=.:apps/api/src .venv/bin/python -m uvicorn policyscope_api.main:app --app-dir apps/api/src --port 8002",
      cwd: "../..",
      url: "http://127.0.0.1:8002/api/health",
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command:
        "VITE_API_PROXY_TARGET=http://127.0.0.1:8002 npm run dev -- --host 127.0.0.1 --port 4182 --strictPort",
      cwd: "../presentation",
      url: "http://127.0.0.1:4182",
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
