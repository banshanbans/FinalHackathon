import { expect, test, type TestInfo } from "@playwright/test";

test("M33.4 event catalog advances seven-round presentation through SSE", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "presentation-1280", "single functional browser matrix");
  await page.goto("/?intro=0");
  await expect(page.getByText("05 项冻结情景")).toBeVisible();
  await expect(page.locator(".event-catalog-grid button")).toHaveCount(5);
  await page.getByRole("button", { name: /L3 企业责任提高/ }).click();
  await page.getByRole("button", { name: "高强度" }).click();
  await page.getByRole("button", { name: "启动演示实验" }).click();

  await expect(page).toHaveURL(/\/experiments\/[^/]+\/present/);
  await expect(page.locator(".maplibregl-marker.territory-map-label")).toHaveCount(3);
  await expect(page.locator(".maplibregl-marker.territory-map-label")).toContainText(["香港", "台湾", "澳门"]);
  await expect(page.getByTitle("SSE 事实流连接状态")).toContainText("LIVE");
  await expect(page.getByRole("button", { name: /NEXT ROUND 省级初始行动/ })).toBeVisible();
  await expect(page.locator(".data-status")).toContainText("FAKE / FALLBACK");
  const experimentId = new URL(page.url()).pathname.split("/")[2];

  await page.context().setOffline(true);
  await expect(page.getByTitle("SSE 事实流连接状态")).toContainText("OFFLINE");
  await expect(page.getByRole("heading", { name: "方案冻结" })).toBeVisible();
  await page.context().setOffline(false);
  await expect(page.getByTitle("SSE 事实流连接状态")).toContainText("LIVE");

  const response = await page.request.post(
    `http://127.0.0.1:8000/api/experiments/${experimentId}/run`,
    { data: { until_round: "province_initial" } },
  );
  expect(response.ok()).toBeTruthy();
  await expect(page.getByRole("heading", { name: "省级初始行动" })).toBeVisible();
  await expect(page.getByRole("button", { name: /NEXT ROUND 车企初步响应/ })).toBeVisible();

  await page.getByRole("button", { name: "事件" }).click();
  await expect(page.getByRole("complementary", { name: "事件详情" })).toContainText("L3 企业责任提高");
  await expect(page.getByRole("complementary", { name: "事件详情" })).toContainText("ACTIVE");
  await expect(page.getByRole("complementary", { name: "事件详情" })).toContainText("不代表现实");
  await page.getByRole("button", { name: "关闭详情" }).click();

  for (const [nextLabel, frameTitle] of [
    ["车企初步响应", "L3 企业责任提高"],
    ["省级策略调整", "省级竞争反制与协同"],
    ["政企谈判", "车企报价与反报价"],
    ["省级回应", "省级反报价回应"],
    ["车企最终行动", "车企最终确认与重配"],
    ["环境结算", "结果复盘"],
  ] as const) {
    await page.getByRole("button", { name: new RegExp(`NEXT ROUND ${nextLabel}`) }).click();
    await expect(page.getByRole("heading", { name: frameTitle })).toBeVisible();
  }
  await expect(page.getByRole("button", { name: "结果对照" })).toBeVisible();
  await expect(page.getByTitle("SSE 事实流连接状态")).toContainText("FROZEN");

  await page.getByRole("button", { name: "章节回放" }).click();
  await page.keyboard.press("Home");
  await expect(page.getByRole("heading", { name: "政策输入" })).toBeVisible();
  await page.keyboard.press("Shift+ArrowRight");
  await expect(page.locator(".chapter-row")).toContainText("企业反馈");
  await page.keyboard.press("Space");
  await expect(page.getByRole("button", { name: "暂停" })).toBeVisible();
  await page.keyboard.press("Space");
  await expect(page.getByRole("button", { name: "播放" })).toBeVisible();
  await page.keyboard.press("r");
  await expect(page.getByRole("heading", { name: "政策输入" })).toBeVisible();

  await page.getByRole("button", { name: "结果对照" }).click();
  await expect(page.getByText(/GAP (收窄|扩大|持平)/)).toBeVisible();
  await expect(page.locator(".mechanism-chain")).toHaveCount(3);
  await page.getByRole("button", { name: "A/B 同步" }).click();
  await expect(page.getByRole("region", { name: "同步 A/B 双世界" })).toBeVisible();
  await expect(page.getByLabel("原始方案省域地图")).toBeVisible();
  await expect(page.getByLabel("干预方案省域地图")).toBeVisible();
  await page.getByRole("button", { name: "Δ 单图" }).click();
  await expect(page.getByLabel("全国省域推演地图")).toBeVisible();

  const speed = page.getByRole("button", { name: "1.0×" });
  await speed.click();
  await expect(page.getByRole("button", { name: "1.5×" })).toBeVisible();
  await page.getByRole("button", { name: "1.5×" }).click();
  await expect(page.getByRole("button", { name: "2.0×" })).toBeVisible();
  await page.getByRole("button", { name: "2.0×" }).click();
  await expect(page.getByRole("button", { name: "0.5×" })).toBeVisible();

  await page.getByRole("button", { name: "章节回放" }).click();
  await page.keyboard.press("Home");
  await page.getByRole("button", { name: "0.5×" }).click();
  await page.getByRole("button", { name: "1.0×" }).click();
  await page.getByRole("button", { name: "1.5×" }).click();
  await page.keyboard.press("Space");
  await expect(page.locator(".chapter-row")).toContainText("11 / 11", { timeout: 25_000 });
  await expect(page.getByRole("button", { name: "播放" })).toBeVisible();

  const dimensions = await page.evaluate(() => ({
    viewport: window.innerWidth,
    scroll: document.documentElement.scrollWidth,
  }));
  expect(dimensions.scroll).toBeLessThanOrEqual(dimensions.viewport);

  await page.goto(`/experiments/${experimentId}/present?intro=0&mapFallback=1`);
  await expect(page.getByText("SVG COMPAT")).toBeVisible();
  await expect(page.locator(".fallback-map path.simulation-province")).toHaveCount(31);
  await expect(page.locator(".fallback-map path.territory-context")).toHaveCount(3);
  await expect(page.locator(".fallback-map text.territory-map-label")).toHaveCount(3);
  for (const name of ["香港", "澳门", "台湾"]) {
    await expect(page.locator(`.fallback-map path[aria-label^="${name}"]`)).toHaveCount(1);
  }
});

test("M33.6 @resolutions completed stage fits 1080p, 2K and 4K", async ({ page }, testInfo: TestInfo) => {
  test.skip(testInfo.project.name === "presentation-1280", "resolution matrix only");
  await page.goto("/?intro=0");
  await page.getByRole("button", { name: "启动演示实验" }).click();
  await expect(page).toHaveURL(/\/experiments\/[^/]+\/present/);
  const experimentId = new URL(page.url()).pathname.split("/")[2];
  const response = await page.request.post(
    `http://127.0.0.1:8000/api/experiments/${experimentId}/run`,
    { data: { until_round: "environment_settlement" } },
  );
  expect(response.ok()).toBeTruthy();
  await page.goto(`/experiments/${experimentId}/present?intro=0`);
  await expect(page.getByRole("button", { name: "结果对照" })).toBeVisible();
  await expect(page.locator(".presentation-map canvas.maplibregl-canvas")).toBeVisible();
  await page.waitForTimeout(1_200);
  const layout = await page.evaluate(() => ({
    viewportWidth: window.innerWidth,
    viewportHeight: window.innerHeight,
    scrollWidth: document.documentElement.scrollWidth,
    scrollHeight: document.documentElement.scrollHeight,
    timelineBottom: document.querySelector(".timeline-rail")?.getBoundingClientRect().bottom ?? 0,
    hudTop: document.querySelector(".top-hud")?.getBoundingClientRect().top ?? -1,
  }));
  expect(layout.scrollWidth).toBeLessThanOrEqual(layout.viewportWidth);
  expect(layout.scrollHeight).toBeLessThanOrEqual(layout.viewportHeight);
  expect(layout.timelineBottom).toBeLessThanOrEqual(layout.viewportHeight);
  expect(layout.hudTop).toBeGreaterThanOrEqual(0);
  await page.screenshot({
    path: `../../outputs/m33-resolution/${testInfo.project.name}.png`,
    fullPage: true,
  });
});
