import { expect, test, type Page, type TestInfo } from "@playwright/test";

type ExperimentType = "policy_comparison" | "policy_stress_test" | "event_counterfactual";

const typeLabels: Record<ExperimentType, string> = {
  policy_comparison: "政策对比",
  policy_stress_test: "政策压力测试",
  event_counterfactual: "事件反事实",
};

async function capture(page: Page, testInfo: TestInfo, name: string) {
  await assertNoHorizontalOverflow(page);
  await page.screenshot({
    path: `../../output/playwright/v32/${testInfo.project.name}/${name}.png`,
    fullPage: true,
  });
}

async function assertNoHorizontalOverflow(page: Page) {
  const dimensions = await page.evaluate(() => ({
    scroll: document.documentElement.scrollWidth,
    viewport: window.innerWidth,
  }));
  expect(dimensions.scroll).toBeLessThanOrEqual(dimensions.viewport);
}

async function createToLive(page: Page, type: ExperimentType) {
  await page.goto("/experiments/new");
  await expect(page.getByRole("heading", { name: "输入待研判的政策文本" })).toBeVisible();
  if (type === "policy_stress_test") {
    await page.getByRole("button", { name: "压力测试" }).click();
  } else if (type === "event_counterfactual") {
    await page.getByRole("button", { name: "事件反事实" }).click();
  }
  await page.getByRole("button", { name: "生成政策解读" }).click();
  await expect(page.getByRole("heading", { name: "确认政策解读" })).toBeVisible();
  await expect(page.getByText("政策解读")).toBeVisible();
  await page.getByRole("button", { name: "确认并设置方案" }).click();
  await expect(page.getByRole("heading", { name: "设置对比方案" })).toBeVisible();
  await page.getByRole("button", { name: new RegExp(`^${typeLabels[type]}`) }).click();
  if (type !== "policy_comparison") {
    await expect(page.getByText("事件计划")).toBeVisible();
    await page.getByLabel("强度").selectOption("high");
  }
  if (type === "event_counterfactual") {
    await expect(page.locator(".v32-share-editor input:disabled")).toHaveCount(3);
  }
  await page.getByRole("button", { name: "确认方案" }).click();
  await expect(page.getByRole("heading", { name: "数据准备完成" })).toBeVisible();
  await page.getByRole("button", { name: "开始推演" }).click();
  await expect(page.getByRole("heading", { name: "全国推演" })).toBeVisible();
  return new URL(page.url()).pathname.split("/")[2];
}

test("V3.2 six-step policy comparison is recoverable and conclusion-first", async (
  { page },
  testInfo,
) => {
  const experimentId = await createToLive(page, "policy_comparison");
  await page.getByRole("button", { name: "北京", exact: true }).click();
  await expect(page.getByRole("dialog", { name: "北京概览" })).toBeVisible();
  await expect(page.locator("body")).not.toContainText("观察、竞争和协作资格均来自冻结关系与实际决策。");
  await capture(page, testInfo, "01-live-ready");
  await page.getByRole("button", { name: "推进下一步" }).click();
  await expect(page.locator(".v32-round-rail .done")).toHaveCount(1);
  await page.reload();
  await expect(page.getByText("省级初始行动", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "完成推演" }).click();
  await expect(page.getByRole("button", { name: "查看结果对比" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "资源竞争" })).toBeVisible();
  await expect(page.locator(".v32-live-page")).not.toContainText(/Agent|M29|M32|Top-K|机会成本|资源上限/);
  await expect(page.getByText(/动态色阶：±.*个百分点/)).toBeVisible();
  await expect(page.locator("body")).not.toContainText(/候选省份|候选池/);
  const market = await (
    await page.request.get(`/api/experiments/${experimentId}/strategy-market`)
  ).json();
  expect(market.automaker_signal_count).toBe(620);
  expect(market.response_count).toBe(market.proposal_count);
  expect(market.schema_version).toBe("strategy-market-v2");
  expect(market.enterprise_response_count).toBe(market.enterprise_offer_count);
  expect(market.enterprise_matched_count).toBeLessThanOrEqual(50);
  const controlMarket = market.branches.control;
  const enterpriseRecords = controlMarket.province_enterprise_matches as Array<{ status: string }>;
  const enterpriseActiveCount = enterpriseRecords.filter((item) => item.status === "matched").length;
  const enterpriseInactiveCount = enterpriseRecords.length - enterpriseActiveCount;
  const ledger = page.locator(".v32-interaction-ledger");
  const ledgerList = ledger.locator(".v32-interaction-list > button");
  await ledger.getByRole("button", { name: `全部 ${enterpriseRecords.length} 项`, exact: true }).click();
  await expect(ledgerList).toHaveCount(Math.min(8, enterpriseRecords.length));
  await expect(ledger.getByRole("navigation", { name: "互动记录分页" })).toBeVisible();
  await ledger.getByRole("button", { name: `${enterpriseActiveCount} 项生效`, exact: true }).click();
  await expect(ledgerList).toHaveCount(Math.min(8, enterpriseActiveCount));
  await expect(ledger.locator(".v32-interaction-list em:not(.matched)")).toHaveCount(0);
  await ledger.getByRole("button", { name: `${enterpriseInactiveCount} 项未生效`, exact: true }).click();
  await expect(ledgerList).toHaveCount(Math.min(8, enterpriseInactiveCount));
  await expect(ledger.locator(".v32-interaction-list em.matched")).toHaveCount(0);

  await ledger.getByRole("button", { name: "省际协同", exact: true }).click();
  const provinceRecords = controlMarket.coordination_records as Array<{ status: string }>;
  const provinceActiveCount = provinceRecords.filter((item) => item.status === "matched").length;
  await ledger.getByRole("button", { name: `全部 ${provinceRecords.length} 项`, exact: true }).click();
  await expect(ledgerList).toHaveCount(Math.min(8, provinceRecords.length));
  await ledger.getByRole("button", { name: `${provinceActiveCount} 项生效`, exact: true }).click();
  await expect(ledger.locator(".v32-interaction-list em:not(.matched)")).toHaveCount(0);
  await expect(page.locator(".v32-metric-strip")).toBeVisible();
  const metricStripIsAboveCanvas = await page.evaluate(() => {
    const metrics = document.querySelector(".v32-metric-strip");
    const canvas = document.querySelector(".v32-live-layout");
    return Boolean(metrics && canvas && (metrics.compareDocumentPosition(canvas) & Node.DOCUMENT_POSITION_FOLLOWING));
  });
  expect(metricStripIsAboveCanvas).toBe(true);
  await capture(page, testInfo, "02-live-complete");

  await page.getByRole("link", { name: "参与主体" }).click();
  await expect(page.getByRole("heading", { name: "31 个省份与 10 家车企" })).toBeVisible();
  await page.getByRole("button", { name: /^北京/ }).click();
  await expect(page.getByRole("heading", { name: "北京方案表现" })).toBeVisible();
  await expect(page.getByText("政策配置", { exact: true })).toBeVisible();
  await expect(page.getByText("企业互动", { exact: true })).toBeVisible();
  await expect(page.getByText("竞争与协同", { exact: true })).toBeVisible();
  await expect(page.getByText("推演影响", { exact: true })).toBeVisible();
  await expect(page.locator(".v32-province-results")).not.toContainText(/为什么|机会成本|资源包|Top-K|Agent/);
  await expect(page.locator("body")).not.toContainText(
    /fiscally_prudent|talent_cost|policy_comparison|province_revision/,
  );
  await capture(page, testInfo, "03-province-decision-trace");

  await page.goto(`/experiments/${experimentId}/participants?company=byd`);
  await expect(page.getByRole("heading", { name: "比亚迪" })).toBeVisible();
  await expect(page.getByText("行动概览")).toBeVisible();
  await capture(page, testInfo, "04-automaker-persona");
  await page.getByRole("button", { name: "关闭" }).click();

  await page.goto(`/experiments/${experimentId}/compare`);
  await expect(page.getByText("结果复盘")).toBeVisible();
  await expect(page.getByText("Gap 方向")).toBeVisible();
  await expect(page.getByText("行动调整")).toBeVisible();
  await expect(page.locator(".v32-company-deltas button")).toHaveCount(10);
  await expect(page.locator("body")).not.toContainText(/policy_comparison|province_initial|Y2_Q2/);
  await capture(page, testInfo, "05-compare-conclusion-first");
  await page.reload();
  await expect(page.getByText("Gap 方向")).toBeVisible();
  await assertNoHorizontalOverflow(page);

  await page.getByRole("button", { name: "打开方法与数据" }).click();
  await expect(page.getByRole("heading", { name: "同源证明、版本、公式与运行记录" })).toBeVisible();
  await expect(page.getByText("两分支来自同一不可变基线快照")).toBeVisible();
  await expect(page.getByText("226 次结构化主体调用")).toBeVisible();
  await capture(page, testInfo, "06-methods-proof");
});

test("policy stress test applies one frozen event to both branches", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "chromium-1440", "Experiment invariant runs once.");
  const experimentId = await createToLive(page, "policy_stress_test");
  await page.getByRole("button", { name: "完成推演" }).click();
  await expect(page.getByRole("button", { name: "查看结果对比" })).toBeVisible();
  const state = await (await page.request.get(`/api/experiments/${experimentId}/state`)).json();
  expect(state.design.experiment_type).toBe("policy_stress_test");
  expect(state.branches.control.event_applied).toBe(true);
  expect(state.branches.treatment.event_applied).toBe(true);
  expect(state.status).toBe("completed");
  await capture(page, testInfo, "07-policy-stress-complete");
});

test("event counterfactual keeps policy fixed and re-evaluates automakers", async (
  { page },
  testInfo,
) => {
  test.skip(testInfo.project.name !== "chromium-1440", "Experiment invariant runs once.");
  const experimentId = await createToLive(page, "event_counterfactual");
  await page.getByRole("button", { name: "完成推演" }).click();
  await expect(page.getByRole("button", { name: "查看结果对比" })).toBeVisible();
  const state = await (await page.request.get(`/api/experiments/${experimentId}/state`)).json();
  expect(state.design.control_policy.west_central_share).toBe(
    state.design.treatment_policy.west_central_share,
  );
  expect(state.branches.control.event_applied).toBe(false);
  expect(state.branches.treatment.event_applied).toBe(true);
  const comparison = await (
    await page.request.get(`/api/experiments/${experimentId}/compare`)
  ).json();
  expect(comparison.active_difference).toBe("event");
  expect(comparison.automaker_deltas.every((item: { changed_province_count: number }) => item.changed_province_count > 0)).toBe(true);
  await page.getByRole("button", { name: "查看结果对比" }).click();
  await expect(page.getByText("10").first()).toBeVisible();
  await capture(page, testInfo, "08-event-counterfactual-compare");
});

test("SSE interruption exposes reconnecting state", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "chromium-1440", "Runtime state is captured once.");
  await page.route("**/api/experiments/*/stream", (route) => route.abort("failed"));
  await createToLive(page, "policy_comparison");
  await expect(page.getByText("推演进度正在恢复")).toBeVisible();
  await capture(page, testInfo, "09-sse-reconnecting");
});
