import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("onboarding_dismissed", "1"));
  await page.route("**/api/greeting*", route => route.fulfill({ json: { greeting: "" } }));
  await page.route("**/api/version", route =>
    route.fulfill({ json: { current_version: "test", update_available: false } }),
  );
});

test("batch runs the bundled set, isolates outcomes and survives reload", async ({ page }) => {
  await page.goto("/");
  await page.getByText("批量评测 · Sprint 2", { exact: true }).click();
  await page.getByRole("button", { name: "运行批次" }).click();

  await expect(page.getByText("完成 10/10", { exact: true })).toBeVisible();
  await expect(page.getByText("通过 2", { exact: true })).toBeVisible();
  await expect(page.getByText("失败 4", { exact: true })).toBeVisible();
  await expect(page.getByText("无法验证 4", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "查看 growth-wrong" }).click();
  const card = page.getByRole("article", { name: "证据验证结果" }).first();
  await expect(card).toContainText("证据验证：失败");
  await expect(card).toContainText("计算结果：10.00%");

  await card.getByText("查看 SQL、证据与执行步骤", { exact: true }).click();
  const trace = card.getByRole("region", { name: "执行轨迹" });
  await expect(trace).toContainText("SQL 查询 · 已完成");
  await trace.getByText("查看对应 SQL 与证据", { exact: true }).click();
  await expect(trace).toContainText("声明引用的证据");
  await expect(trace.locator("pre")).toHaveCount(1);

  await page.reload();
  await page.getByText("批量评测 · Sprint 2", { exact: true }).click();
  await expect(page.getByText("完成 10/10", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "查看 growth-exact" })).toBeVisible();
});

test("mixed rules can be selected and retain SQL, source and history after reload", async ({ page }) => {
  await page.goto("/");
  await page.getByText("批量评测 · Sprint 2", { exact: true }).click();
  const selector = page.getByLabel("案例集", { exact: true });
  await expect(selector).toHaveValue("sprint2-sales-v1");
  await selector.selectOption("sprint2-sales-mixed-v1");
  await expect(page.getByText("固定测试声明（非真实模型输出）", { exact: false })).toBeVisible();
  const request = page.waitForRequest(req =>
    req.method() === "POST" && req.url().endsWith("/api/harness/batches"),
  );
  await page.getByRole("button", { name: "运行批次" }).click();
  expect((await request).postDataJSON().case_set_id).toBe("sprint2-sales-mixed-v1");
  await expect(page.getByText("完成 8/8", { exact: true })).toBeVisible();
  await expect(page.getByText("通过 3", { exact: true })).toBeVisible();
  await expect(page.getByText("失败 2", { exact: true })).toBeVisible();
  await expect(page.getByText("无法验证 3", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "查看 total-one-cent-error" }).click();
  const card = page.getByRole("article", { name: "证据验证结果" }).first();
  await expect(card).toContainText("证据验证：失败");
  await expect(card).toContainText("11000");
  await expect(card).toContainText("CNY_cent");
  await card.getByText("查看 SQL、证据与执行步骤", { exact: true }).click();
  const trace = card.getByRole("region", { name: "执行轨迹" });
  await expect(trace).toContainText("SQL 查询 · 已完成");
  await trace.getByText("查看对应 SQL 与证据", { exact: true }).click();
  await expect(trace.locator("pre")).toHaveCount(1);
  await expect(trace).toContainText("sales_records");

  await page.reload();
  await page.getByText("批量评测 · Sprint 2", { exact: true }).click();
  await expect(page.getByText("完成 8/8", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "查看 total-fractional-cent" })).toBeVisible();
  // Changing the next input must not relabel the persisted batch being displayed.
  await page.getByLabel("案例集", { exact: true }).selectOption("sprint2-sales-v1");
  await expect(page.getByText(/批次 .+ · completed · sprint2-sales-mixed-v1 v1/)).toBeVisible();
});

test("catalog failure disables new execution while preserving history access", async ({ page, request }) => {
  const batch = await request.post("/api/harness/batches", {
    data: { case_set_id: "sprint2-sales-mixed-v1" },
  });
  expect(batch.status()).toBe(201);
  await page.route("**/api/harness/batches/case-sets", route =>
    route.fulfill({ status: 503, json: { detail: "unavailable" } }),
  );
  await page.goto("/");
  await page.getByText("批量评测 · Sprint 2", { exact: true }).click();
  await expect(page.getByText("案例集读取失败，请刷新页面重试。")).toBeVisible();
  await expect(page.getByRole("button", { name: "运行批次" })).toBeDisabled();
  await expect(page.getByText("完成 8/8", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "查看 total-one-cent-error" }).click();
  await expect(page.getByRole("article", { name: "证据验证结果" }).first()).toContainText("证据验证：失败");
});
