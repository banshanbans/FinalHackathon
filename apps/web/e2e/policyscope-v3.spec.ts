import { expect, test, type APIRequestContext, type Page, type TestInfo } from "@playwright/test";

const API = "http://127.0.0.1:8000/api";

function policy(source: Record<string, unknown>, policyId: string, delta = 0) {
  return {
    ...source,
    policy_id: policyId,
    west_central_share: Number(source.west_central_share) + delta,
    central_central_share: Number(source.central_central_share) + delta,
    east_central_share: Number(source.east_central_share) + delta,
  };
}

async function prepareCompleted(request: APIRequestContext) {
  const key = `web-e2e-${Date.now()}-${Math.random()}`;
  const createdResponse = await request.post(`${API}/experiments`, {
    headers: { "Idempotency-Key": key },
    data: {
      product_version: "v3_2_m34",
      policy_text: "评估新能源汽车补贴三档中央承担比例的年度同源差异。",
      seed: 20260813,
    },
  });
  expect(createdResponse.status()).toBe(201);
  const created = await createdResponse.json();
  const id = created.experiment_id as string;
  await request.put(`${API}/experiments/${id}/interpretation`, {
    data: { ...created.interpretation, status: "confirmed" },
  });
  const base = created.interpretation.executable_policy as Record<string, unknown>;
  await request.put(`${API}/experiments/${id}/design`, {
    data: {
      schema_version: "experiment-design-v2",
      experiment_type: "policy_comparison",
      control_policy: policy(base, "control"),
      treatment_policy: policy(base, "treatment", 0.02),
      event_plans: [],
      status: "confirmed",
    },
  });
  const baseline = await (await request.get(`${API}/meta/v32/baseline`)).json();
  await request.post(`${API}/experiments/${id}/baseline/confirm`, {
    data: { confirm_data_snapshot: true, expected_data_version: baseline.data_version },
  });
  const run = await request.post(`${API}/experiments/${id}/run`, {
    headers: { "Idempotency-Key": `${key}:Q4` },
    data: { until_tick: "Q4" },
  });
  expect(run.ok()).toBeTruthy();
  return id;
}

async function expectNoOverflow(page: Page) {
  const dimensions = await page.evaluate(() => ({
    width: window.innerWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.width);
}

test("M34 workbench creates a policy interpretation and reaches quarterly design", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "chromium-1536", "creation journey runs once");
  await page.goto("/experiments/new");
  await expect(page.getByRole("heading", { name: "输入待研判的政策文本" })).toBeVisible();
  await page.getByRole("button", { name: "生成中央政策解读" }).click();
  await expect(page.getByRole("heading", { name: "确认中央政策解读" })).toBeVisible();
  await page.getByRole("button", { name: "确认解读" }).click();
  await expect(page.getByRole("heading", { name: "设置年度季度方案" })).toBeVisible();
  await expect(page.getByText("外生事件 0 / 3")).toBeVisible();
  await page.getByRole("button", { name: "确认季度设计" }).click();
  await expect(page.getByRole("heading", { name: "确认同源基线" })).toBeVisible();
  await page.getByRole("button", { name: "确认基线并进入推演" }).click();
  await expect(page.getByRole("heading", { name: "Q1 待运行" })).toBeVisible();
  await expect(page.getByRole("button", { name: "运行 Q1" })).toBeVisible();
  await expectNoOverflow(page);
});

test("M34 completed workbench and comparison fit supported canvases", async ({ page, request }, testInfo: TestInfo) => {
  const id = await prepareCompleted(request);
  await page.goto(`/experiments/${id}/live`);
  await expect(page.getByRole("heading", { name: "Q4 年度结果已冻结" })).toBeVisible();
  await expect(page.getByText("模拟季度与互动顺序，不代表现实响应日期。")).toBeVisible();
  await expect(page.locator(".v3-flow-strip > div.done")).toHaveCount(4);
  await expectNoOverflow(page);
  await page.screenshot({
    path: `../../output/playwright/m34-workbench/${testInfo.project.name}-live.png`,
    fullPage: true,
  });

  await page.getByRole("link", { name: "查看年度比较" }).click();
  await expect(page.getByText("唯一主动差异：政策")).toBeVisible();
  await expect(page.getByText("中央 Agent · 实验后唯一一次")).toBeVisible();
  await expectNoOverflow(page);
});

test("legacy M32 deep links show the stable 410 boundary", async ({ request }, testInfo) => {
  test.skip(testInfo.project.name !== "chromium-1536", "legacy boundary runs once");
  const response = await request.get(`${API}/experiments/exp_m32_e2elegacy/state`);
  expect(response.status()).toBe(410);
  expect((await response.json()).detail.error_code).toBe("LEGACY_V32_RUNTIME_UNSUPPORTED");
});
