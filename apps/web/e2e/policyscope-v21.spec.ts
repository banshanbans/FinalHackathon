import { expect, test, type Page, type TestInfo } from "@playwright/test";

async function capture(page: Page, testInfo: TestInfo, name: string) {
  if (process.env.POLICYSCOPE_CAPTURE !== "1") return;
  await page.screenshot({
    path: `../../output/playwright/v21/${testInfo.project.name}/${name}.png`,
    fullPage: true,
  });
}

async function createAndRunToT3(page: Page, testInfo: TestInfo) {
  await page.goto("/experiments/new");
  await expect(page.getByRole("heading", { name: "配置制造业设备更新政策" })).toBeVisible();
  await page.getByRole("button", { name: /生成结构化政策草案/ }).click();
  await expect(page.getByText("政策草案待审")).toBeVisible();
  await capture(page, testInfo, "01-policy-draft");
  await page.getByRole("button", { name: /批准并启动省企推演/ }).click();
  await expect(page.getByRole("heading", { name: "31 省政策决策与企业反馈" })).toBeVisible();
  await page.getByRole("button", { name: /启动推演至 T3/ }).click();
  await expect(page.getByRole("button", { name: /审批中央干预/ })).toBeVisible({ timeout: 60_000 });
  await capture(page, testInfo, "02-live-t3");
}

test("complete A/B flow prioritizes province decisions", async ({ page }, testInfo) => {
  await createAndRunToT3(page, testInfo);

  await page.getByRole("button", { name: /河南·普惠融资/ }).click();
  await expect(page.getByRole("heading", { name: "河南省" })).toBeVisible();
  await expect(page.getByText("普惠扩散型", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "实验决策画像" })).toBeVisible();
  await expect(page.locator(".enterprise-card")).toHaveCount(6);
  await capture(page, testInfo, "03-province-henan");

  const detailUrl = new URL(page.url());
  detailUrl.searchParams.set("evidence", "method");
  await page.goto(detailUrl.toString());
  await expect(page.getByRole("heading", { name: "运行审计信息" })).toBeVisible();
  await page.getByRole("button", { name: "关闭抽屉" }).click();
  await page.getByRole("button", { name: "31 省决策全景" }).click();
  await page.getByRole("button", { name: /审批中央干预/ }).click();
  await expect(page.getByRole("heading", { name: "中央政策干预审批" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "地方决策证据" })).toBeVisible();
  await capture(page, testInfo, "04-intervention-review");

  await page.getByRole("button", { name: /批准并创建干预方案/ }).click();
  await expect(page.getByText("干预分支已就绪")).toBeVisible();
  await page.getByRole("button", { name: /运行双方案至 T5/ }).click();
  await expect(page.getByRole("heading", { name: "原始方案与干预方案对照" })).toBeVisible({ timeout: 60_000 });
  await expect(page.getByRole("heading", { name: "省级策略迁移" })).toBeVisible();
  await capture(page, testInfo, "05-compare-t5");

  const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
  const viewportWidth = await page.evaluate(() => window.innerWidth);
  expect(scrollWidth).toBe(viewportWidth);
});

test("rejecting the proposal completes a single control branch", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "chromium-1440", "The second flow only needs one desktop run.");
  await createAndRunToT3(page, testInfo);
  await page.getByRole("button", { name: /审批中央干预/ }).click();
  await page.getByRole("button", { name: /驳回并保留原始方案/ }).click();
  await expect(page.getByText("已保留原始方案")).toBeVisible();
  await page.getByRole("button", { name: /运行原始方案至 T5/ }).click();
  await expect(page.getByRole("heading", { name: "原始方案结算结果" })).toBeVisible({ timeout: 60_000 });
});
