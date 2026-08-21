import { expect, test } from "@playwright/test";

test.setTimeout(90_000);

test("loads only local assets and scrolls continuously from cockpit to final stage", async ({ page }) => {
  const externalRequests: string[] = [];
  const consoleErrors: string[] = [];
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.hostname !== "127.0.0.1") externalRequests.push(request.url());
  });
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  await page.setViewportSize({ width: 1440, height: 1024 });
  await page.goto("/");
  await expect(page.locator(".cockpit-frame")).toBeVisible();
  await expect(page.locator("h1")).toHaveCount(0);
  await expect(page.getByText("让政策影响，被看见。")).toHaveCount(0);
  await expect(page.locator(".roadshow")).toHaveAttribute("data-stage", "cockpit");
  const canvas = page.locator("canvas");
  await expect(canvas).toHaveCount(1);
  for (let index = 0; index < 54; index += 1) {
    await page.mouse.wheel(0, 420);
    await page.waitForTimeout(90);
  }
  await expect(page.locator(".roadshow")).toHaveAttribute("data-stage", "earth-return", {
    timeout: 16_000,
  });
  await expect(page.getByRole("img", { name: "从无品牌新能源汽车座舱内望向高位单柱省级政策信号屏" })).toBeVisible();
  await expect(canvas).toHaveCount(1);
  await expect(page.locator(".flat-china-map")).toHaveCount(0);
  expect(externalRequests).toEqual([]);
  expect(consoleErrors).toEqual([]);
  await page.close({ runBeforeUnload: false });
});

test("reduced motion enters the stable terminal frame directly", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await expect(page.locator(".roadshow")).toHaveAttribute("data-stage", "earth-return");
  await expect(page.locator(".vehicle-world")).toBeVisible();
});

test("wheel input advances virtual progress without moving or remounting the WebGL stage", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.goto("/");
  await expect(page.locator(".roadshow")).toHaveAttribute("data-stage", "cockpit");
  const canvas = page.locator("canvas");
  await expect(canvas).toHaveCount(1);
  for (let index = 0; index < 54; index += 1) {
    await page.mouse.wheel(0, 420);
    await page.waitForTimeout(80);
  }
  await expect(page.locator(".roadshow")).toHaveAttribute("data-stage", "earth-return", {
    timeout: 5_000,
  });
  const metrics = await page.evaluate(() => ({
    scrollY: window.scrollY,
    scrollHeight: document.documentElement.scrollHeight,
    innerHeight: window.innerHeight,
  }));
  expect(metrics.scrollY).toBe(0);
  expect(metrics.scrollHeight).toBe(metrics.innerHeight);
  await expect(canvas).toHaveCount(1);
  expect(consoleErrors).toEqual([]);
  await page.close({ runBeforeUnload: false });
});

test("all arrow keys control the same reversible timeline", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator(".roadshow")).toHaveAttribute("data-stage", "cockpit");
  await expect(page.locator(".roadshow")).toBeFocused();

  for (let index = 0; index < 16; index += 1) await page.keyboard.press("ArrowRight");
  await expect(page.locator(".roadshow")).toHaveAttribute("data-stage", "china-focus", { timeout: 8_000 });

  for (let index = 0; index < 16; index += 1) await page.keyboard.press("ArrowLeft");
  await expect(page.locator(".roadshow")).toHaveAttribute("data-stage", "cockpit", { timeout: 8_000 });

  for (let index = 0; index < 16; index += 1) await page.keyboard.press("ArrowDown");
  await expect(page.locator(".roadshow")).toHaveAttribute("data-stage", "china-focus", { timeout: 8_000 });

  for (let index = 0; index < 16; index += 1) await page.keyboard.press("ArrowUp");
  await expect(page.locator(".roadshow")).toHaveAttribute("data-stage", "cockpit", { timeout: 8_000 });
  await expect(page.locator("canvas")).toHaveCount(1);
});

for (const viewport of [
  { width: 1280, height: 720 },
  { width: 1920, height: 1080 },
  { width: 2560, height: 1440 },
  { width: 3840, height: 2160 },
]) {
  test(`keeps the stage inside ${viewport.width}x${viewport.height}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/");
    await expect(page.locator(".roadshow")).toHaveAttribute("data-stage", "earth-return");
    const metrics = await page.evaluate(() => ({
      bodyWidth: document.body.scrollWidth,
      viewportWidth: window.innerWidth,
      vehicle: document.querySelector(".vehicle-world")?.getBoundingClientRect().toJSON(),
    }));
    expect(metrics.bodyWidth).toBeLessThanOrEqual(metrics.viewportWidth);
    expect(metrics.vehicle?.left).toBeGreaterThanOrEqual(0);
    expect(metrics.vehicle?.right).toBeLessThanOrEqual(viewport.width);
    expect(metrics.vehicle?.bottom).toBeLessThanOrEqual(viewport.height);
  });
}
