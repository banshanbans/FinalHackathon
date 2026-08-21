import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

const API = "http://127.0.0.1:8002/api";
const SCREENSHOTS = "../../docs/assets/readme";

function policy(source: Record<string, unknown>, policyId: string, delta = 0) {
  return {
    ...source,
    policy_id: policyId,
    west_central_share: Number(source.west_central_share) + delta,
    central_central_share: Number(source.central_central_share) + delta,
    east_central_share: Number(source.east_central_share) + delta,
  };
}

async function createReadmeFixture(request: APIRequestContext) {
  const operationId = `readme-${Date.now()}`;
  const createdResponse = await request.post(`${API}/experiments`, {
    headers: { "Idempotency-Key": `readme:create:${operationId}` },
    data: {
      product_version: "v3_2_m34",
      policy_text: "西部 95%，中部 90%，东部 85%，进行年度同源对比。",
      seed: 20260813,
    },
  });
  expect(createdResponse.status()).toBe(201);
  const created = await createdResponse.json();
  const experimentId = created.experiment_id as string;

  const interpretation = await request.put(`${API}/experiments/${experimentId}/interpretation`, {
    data: { ...created.interpretation, status: "confirmed" },
  });
  expect(interpretation.ok()).toBeTruthy();

  const base = created.interpretation.executable_policy as Record<string, unknown>;
  const design = await request.put(`${API}/experiments/${experimentId}/design`, {
    data: {
      schema_version: "experiment-design-v2",
      experiment_type: "policy_comparison",
      control_policy: policy(base, "control"),
      treatment_policy: policy(base, "treatment", 0.02),
      event_plans: [],
      status: "confirmed",
    },
  });
  expect(design.ok()).toBeTruthy();

  const baselineMeta = await (await request.get(`${API}/meta/v32/baseline`)).json();
  const baseline = await request.post(`${API}/experiments/${experimentId}/baseline/confirm`, {
    data: { confirm_data_snapshot: true, expected_data_version: baselineMeta.data_version },
  });
  expect(baseline.ok()).toBeTruthy();

  const run = await request.post(`${API}/experiments/${experimentId}/run`, {
    headers: { "Idempotency-Key": `readme:run:${experimentId}:Q4` },
    data: { until_tick: "Q4" },
  });
  expect(run.ok()).toBeTruthy();
  return experimentId;
}

async function settleVisuals(page: Page) {
  await expect(page.locator(".presentation-map-canvas")).toBeVisible();
  await page.evaluate(async () => {
    await document.fonts.ready;
    await new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve())));
  });
}

test("capture README product screenshots from one deterministic fixture", async ({ page, request }) => {
  const experimentId = await createReadmeFixture(request);
  await page.goto(`/experiments/${experimentId}/present`);
  await expect(page.getByText("年度事实已冻结")).toBeVisible();
  await expect(page.locator(".comparison-panel")).toBeVisible();
  await settleVisuals(page);
  await page.screenshot({
    path: `${SCREENSHOTS}/annual-comparison.jpg`,
    type: "jpeg",
    quality: 90,
  });

  await page.getByRole("button", { name: "Q1 · 首次行动", exact: true }).click();
  await page.locator(".beat-list > button").nth(3).click();
  await expect(page.locator(".game-action.action-proposal")).toBeVisible();
  await settleVisuals(page);
  await page.screenshot({
    path: `${SCREENSHOTS}/interaction.jpg`,
    type: "jpeg",
    quality: 90,
  });
});
