import { expect, test, type APIRequestContext, type Page, type TestInfo } from "@playwright/test";

type ExperimentType = "policy_comparison" | "policy_stress_test" | "event_counterfactual";

const API = "http://127.0.0.1:8001/api";

function policy(source: Record<string, unknown>, policyId: string, delta = 0) {
  return {
    ...source,
    policy_id: policyId,
    west_central_share: Number(source.west_central_share) + delta,
    central_central_share: Number(source.central_central_share) + delta,
    east_central_share: Number(source.east_central_share) + delta,
  };
}

function eventPlan(index: number, scope: "both" | "treatment_only") {
  return {
    schema_version: "event-plan-v2",
    event_plan_id: `e2e-event-${index}`,
    template_id: `e2e-template-${index}`,
    name: `季度压力事件 ${index}`,
    description: "用于正式浏览器验收的冻结情景假设",
    conflict_group: null,
    scheduled_tick: (["Q2", "Q3", "Q4"] as const)[index - 1],
    release_wave: (["wave_0", "wave_1", "wave_2"] as const)[index - 1],
    branch_scope: scope,
    advance_notice: false,
    informed_agent_types: [],
    affected_subjects: ["province", "automaker"],
    mechanism_channels: ["demand", "industry"],
    intensity: "medium",
    data_quality: "scenario_assumption",
    evidence_refs: [`scenario:e2e-${index}`],
  };
}

async function createCompletedExperiment(request: APIRequestContext, type: ExperimentType) {
  const operationId = `${type}-${Date.now()}-${Math.random()}`;
  const createdResponse = await request.post(`${API}/experiments`, {
    headers: { "Idempotency-Key": `e2e:create:${operationId}` },
    data: {
      product_version: "v3_2_m34",
      policy_text: "西部 95%，中部 90%，东部 85%，进行年度同源对比。",
      seed: 20260813,
    },
  });
  expect(createdResponse.status()).toBe(201);
  const created = await createdResponse.json();
  const experimentId = created.experiment_id as string;
  expect(experimentId).toMatch(/^exp_m34_/);

  const interpretationResponse = await request.put(`${API}/experiments/${experimentId}/interpretation`, {
    data: { ...created.interpretation, status: "confirmed" },
  });
  expect(interpretationResponse.ok()).toBeTruthy();

  const base = created.interpretation.executable_policy as Record<string, unknown>;
  const eventScope = type === "event_counterfactual" ? "treatment_only" : "both";
  const eventPlans = type === "policy_comparison" ? [] : [eventPlan(1, eventScope)];
  const treatment = type === "event_counterfactual"
    ? policy(base, "treatment")
    : policy(base, "treatment", 0.02);
  const designResponse = await request.put(`${API}/experiments/${experimentId}/design`, {
    data: {
      schema_version: "experiment-design-v2",
      experiment_type: type,
      control_policy: policy(base, "control"),
      treatment_policy: treatment,
      event_plans: eventPlans,
      status: "confirmed",
    },
  });
  expect(designResponse.ok()).toBeTruthy();

  const baselineMeta = await (await request.get(`${API}/meta/v32/baseline`)).json();
  const baselineResponse = await request.post(`${API}/experiments/${experimentId}/baseline/confirm`, {
    data: { confirm_data_snapshot: true, expected_data_version: baselineMeta.data_version },
  });
  expect(baselineResponse.ok()).toBeTruthy();
  const runResponse = await request.post(`${API}/experiments/${experimentId}/run`, {
    headers: { "Idempotency-Key": `e2e:run:${experimentId}:Q4` },
    data: { until_tick: "Q4" },
  });
  expect(runResponse.ok()).toBeTruthy();
  return experimentId;
}

async function expectCanvasFits(page: Page) {
  await expect(page.getByText("年度已冻结")).toBeVisible();
  await expect(page.getByText("模拟季度与互动顺序，不代表现实响应日期")).toBeVisible();
  await expect(page.locator(".m34-quarter-bands > span")).toHaveCount(4);
  const layout = await page.evaluate(() => ({
    width: window.innerWidth,
    height: window.innerHeight,
    scrollWidth: document.documentElement.scrollWidth,
    scrollHeight: document.documentElement.scrollHeight,
    timelineBottom: document.querySelector(".m34-timeline")?.getBoundingClientRect().bottom ?? 0,
  }));
  expect(layout.scrollWidth).toBeLessThanOrEqual(layout.width);
  expect(layout.scrollHeight).toBeLessThanOrEqual(layout.height);
  expect(layout.timelineBottom).toBeLessThanOrEqual(layout.height);
}

for (const experimentType of ["policy_comparison", "policy_stress_test", "event_counterfactual"] as const) {
  test(`${experimentType} completes as a quarterly M34 experiment`, async ({ page, request }, testInfo) => {
    test.skip(testInfo.project.name !== "presentation-1280", "three-type semantic matrix runs once");
    const experimentId = await createCompletedExperiment(request, experimentType);
    const state = await (await request.get(`${API}/experiments/${experimentId}/state`)).json();
    expect(state.design.experiment_type).toBe(experimentType);
    expect(state.branches.control.completed_ticks).toEqual(["Q1", "Q2", "Q3", "Q4"]);
    expect(state.branches.treatment.completed_ticks).toEqual(["Q1", "Q2", "Q3", "Q4"]);
    expect(state.central_call_count).toBe(2);
    if (experimentType === "policy_stress_test") {
      expect(state.design.event_plans[0].branch_scope).toBe("both");
    }
    if (experimentType === "event_counterfactual") {
      expect(state.design.control_policy.west_central_share).toBe(
        state.design.treatment_policy.west_central_share,
      );
      expect(state.design.event_plans[0].branch_scope).toBe("treatment_only");
    }

    await page.goto(`/experiments/${experimentId}/present`);
    await expectCanvasFits(page);
    await page.getByRole("button", { name: "Q1 wave 0 互动", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Q1 wave 0 互动", exact: true })).toBeVisible();
    await page.getByRole("button", { name: "互动", exact: true }).click();
    await expect(page.getByRole("heading", { name: "互动下钻" })).toBeVisible();
    await expect(page.locator(".m34-message").first()).toBeVisible();
  });
}

test("completed M34 timeline fits required presentation canvases", async ({ page, request }, testInfo: TestInfo) => {
  test.skip(testInfo.project.name === "presentation-1280", "required resolution matrix only");
  const experimentId = await createCompletedExperiment(request, "policy_stress_test");
  await page.goto(`/experiments/${experimentId}/present`);
  await expectCanvasFits(page);
  await page.screenshot({
    path: `../../outputs/m34-resolution/${testInfo.project.name}.png`,
    fullPage: true,
  });
});

test("SVG fallback remains a complete 31-province canvas", async ({ page, request }, testInfo) => {
  test.skip(testInfo.project.name !== "presentation-1080p", "fallback canvas runs once");
  const experimentId = await createCompletedExperiment(request, "policy_comparison");
  await page.goto(`/experiments/${experimentId}/present?mapFallback=1`);
  await expect(page.getByText("SVG COMPAT")).toBeVisible();
  await expect(page.locator(".fallback-map path.simulation-province")).toHaveCount(31);
  await expect(page.locator(".fallback-map path.territory-context")).toHaveCount(3);
  await expectCanvasFits(page);
  await page.screenshot({ path: "../../outputs/m34-resolution/presentation-fallback-1920x1080.png" });
});
