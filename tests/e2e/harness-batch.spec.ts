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

  await page.reload();
  await page.getByText("批量评测 · Sprint 2", { exact: true }).click();
  await expect(page.getByText("完成 10/10", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "查看 growth-exact" })).toBeVisible();
});
