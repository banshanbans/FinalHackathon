import { expect, test, type Page, type TestInfo } from "@playwright/test";

async function capture(page: Page, testInfo: TestInfo, name: string) {
  if (process.env.POLICYSCOPE_CAPTURE !== "1") return;
  await page.screenshot({
    path: `../../output/playwright/v3/${testInfo.project.name}/${name}.png`,
    fullPage: true,
  });
}

async function createAndRunYearOne(page: Page, testInfo: TestInfo) {
  await page.goto("/experiments/new");
  await expect(
    page.getByRole("heading", { name: "新能源汽车补贴共担比例实验" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "生成中央政策草案" }).click();
  await expect(page.getByText("Agent 摘要")).toBeVisible();
  await expect(page.getByLabel("西部 12 省中央承担比例")).toHaveValue("95");
  await capture(page, testInfo, "01-policy-draft");

  await page.getByRole("button", { name: "批准并进入首年推演" }).click();
  await expect(
    page.getByRole("heading", { name: "全国新能源汽车政策态势" }),
  ).toBeVisible();
  const experimentId = new URL(page.url()).pathname.split("/")[2];
  await page.request.post(`/api/experiments/${experimentId}/run`, {
    data: { until_phase: "Y1_Q1", branch_id: "control" },
    headers: { "Idempotency-Key": `e2e-y1-q1-${experimentId}` },
  });
  await page.reload();
  await expect(page.getByText("Y1_Q1 · 原始方案")).toBeVisible();
  await capture(page, testInfo, "02-live-y1-q1");
  await page.request.post(`/api/experiments/${experimentId}/run`, {
    data: { until_phase: "Y1_Q2", branch_id: "control" },
    headers: { "Idempotency-Key": `e2e-y1-q2-${experimentId}` },
  });
  await page.reload();
  await page.getByRole("button", { name: "车企销售投入" }).click();
  await capture(page, testInfo, "03-live-y1-q2-automaker-layer");
  await page.getByRole("button", { name: "继续至首年复盘" }).click();
  await expect(page.getByRole("button", { name: "进入干预审批" })).toBeVisible({
    timeout: 60_000,
  });
  await expect(page.getByText("10 家车企 Agent")).toBeVisible();
  await capture(page, testInfo, "04-year1-review");
}

test("complete A/B flow exposes province, company and evidence detail", async (
  { page },
  testInfo,
) => {
  await createAndRunYearOne(page, testInfo);

  await page.getByRole("button", { name: "河南", exact: true }).click();
  await expect(page.getByRole("heading", { name: "河南省" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "地方政策工具" })).toBeVisible();
  await expect(page.getByRole("heading", { name: /10 家全国性 Agent/ })).toBeVisible();
  await capture(page, testInfo, "05-province-henan");

  const detailUrl = new URL(page.url());
  detailUrl.searchParams.set("company", "byd");
  await page.goto(detailUrl.toString());
  await expect(page.getByRole("heading", { name: "比亚迪" })).toBeVisible();
  await expect(page.getByText(/31 省投入组合/)).toBeVisible();
  await capture(page, testInfo, "06-company-byd");
  await page.locator(".v3-drawer-close").click();
  await page.getByRole("button", { name: /返回全国地图/ }).click();

  const liveUrl = new URL(page.url());
  liveUrl.searchParams.set("evidence", "metric:national:regional_development_gap");
  await page.goto(liveUrl.toString());
  await expect(page.getByRole("heading", { name: "方法与证据" })).toBeVisible();
  await expect(page.getByText(/nev-policy-env-v1/)).toBeVisible();
  await capture(page, testInfo, "07-evidence");
  await page.locator(".v3-drawer-close").click();

  await page.getByRole("button", { name: "进入干预审批" }).click();
  await expect(
    page.getByRole("heading", { name: "证据 → 中央建议 → 人工审批" }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "中央 Agent 建议" })).toBeVisible();
  await capture(page, testInfo, "08-intervention-review");

  await page.getByRole("button", { name: "批准/修改后创建 A/B" }).click();
  await expect(page.getByRole("heading", { name: "同源 A/B 尚未结算" })).toBeVisible();
  await page.getByRole("button", { name: "运行次年同源 A/B" }).click();
  await expect(page.getByRole("heading", { name: "原始方案 / 干预方案" })).toBeVisible({
    timeout: 60_000,
  });
  await expect(page.getByText("ΔGap", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "原始方案 · 省级发展指数" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "干预方案 · 省级发展指数" })).toBeVisible();
  await expect(page.locator(".v3-transition-grid button")).toHaveCount(10);
  await capture(page, testInfo, "09-compare-complete");

  await page.reload();
  await expect(page.getByRole("heading", { name: "原始方案 / 干预方案" })).toBeVisible({
    timeout: 60_000,
  });
  await expect(page.locator(".v3-transition-grid button")).toHaveCount(10);

  const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
  const viewportWidth = await page.evaluate(() => window.innerWidth);
  expect(scrollWidth).toBe(viewportWidth);
});

test("rejecting intervention completes only the original branch", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "chromium-1440", "Single-branch flow runs once.");
  await createAndRunYearOne(page, testInfo);
  await page.getByRole("button", { name: "进入干预审批" }).click();
  await page.getByRole("button", { name: "拒绝干预，仅运行原始方案" }).click();
  await expect(page.getByRole("heading", { name: "用户拒绝干预" })).toBeVisible({
    timeout: 60_000,
  });
  await expect(page.getByRole("heading", { name: "原始方案次年结果" })).toBeVisible();
  await expect(page.getByText(/不生成或伪造 A\/B 比较/)).toBeVisible();
});

test("non-monotonic shares warn without blocking the experiment", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "chromium-1440", "Warning state is captured once.");
  await page.goto("/experiments/new");
  await page.getByRole("button", { name: "生成中央政策草案" }).click();
  await expect(page.getByText("Agent 摘要")).toBeVisible();
  await page.getByLabel("西部 12 省中央承担比例").fill("80");
  await expect(page.getByRole("alert")).toContainText("允许继续用于机制实验");
  await expect(page.getByRole("button", { name: "批准并进入首年推演" })).toBeEnabled();
  await capture(page, testInfo, "00-non-monotonic-warning");
});

test("SSE interruption exposes a reconnecting state", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "chromium-1440", "Runtime state is captured once.");
  await page.route("**/api/experiments/*/stream", (route) => route.abort("failed"));
  await page.goto("/experiments/new");
  await page.getByRole("button", { name: "生成中央政策草案" }).click();
  await expect(page.getByText("Agent 摘要")).toBeVisible();
  await page.getByRole("button", { name: "批准并进入首年推演" }).click();
  await expect(page.getByText("事件流正在重连")).toBeVisible();
  await capture(page, testInfo, "10-reconnecting");
});

test("cache miss exposes deterministic fallback scope", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "chromium-1440", "Fallback state is captured once.");
  const health = await page.request.get("/api/health");
  const runtime = (await health.json()) as { run_mode: string };
  test.skip(runtime.run_mode !== "cache", "Requires an intentionally empty cache runtime.");
  await page.goto("/experiments/new");
  await page.getByRole("button", { name: "生成中央政策草案" }).click();
  await expect(page.getByText("Agent 摘要")).toBeVisible();
  await page.getByRole("button", { name: "批准并进入首年推演" }).click();
  await expect(page.getByRole("heading", { name: "全国新能源汽车政策态势" })).toBeVisible();
  const experimentId = new URL(page.url()).pathname.split("/")[2];
  const response = await page.request.post(`/api/experiments/${experimentId}/run`, {
    data: { until_phase: "Y1_Q1", branch_id: "control" },
    headers: { "Idempotency-Key": `fallback-y1-q1-${experimentId}` },
  });
  expect(response.ok()).toBeTruthy();
  await page.reload();
  await expect(page.getByText("确定性 Fallback 已接管")).toBeVisible();
  await expect(page.getByText(/31 个省级主体 · 0 家车企/)).toBeVisible();
  await capture(page, testInfo, "11-fallback");
});
