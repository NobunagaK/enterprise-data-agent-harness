import { expect, test } from "@playwright/test";

test("batch runs the bundled set, isolates outcomes and survives reload", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("onboarding_dismissed", "1"));
  await page.route("**/api/greeting*", route => route.fulfill({ json: { greeting: "" } }));
  await page.route("**/api/version", route =>
    route.fulfill({ json: { current_version: "test", update_available: false } }),
  );
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
