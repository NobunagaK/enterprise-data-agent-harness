import { expect, test } from "@playwright/test";

test("fixed SQL evidence, failed claim and history survive page reload", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("onboarding_dismissed", "1"));
  // Isolate unrelated greeting/release lookups. Harness HTTP and SQL remain real.
  await page.route("**/api/greeting*", route => route.fulfill({ json: { greeting: "" } }));
  await page.route("**/api/version", route => route.fulfill({ json: { current_version: "test", update_available: false } }));
  await page.goto("/");
  await page.getByText("销售增长率验证 · Sprint 1", { exact: true }).click();
  await page.getByRole("button", { name: "运行验证" }).click();
  await expect(page.getByText("证据验证：通过", { exact: true })).toBeVisible();
  await page.getByLabel("声明增长率", { exact: true }).fill("18.7");
  await page.getByRole("button", { name: "运行验证" }).click();
  const card = page.getByRole("article", { name: "证据验证结果" }).first();
  await expect(card).toContainText("证据验证：失败");
  await expect(card).toContainText("计算结果：10.00%");
  await expect(card).toContainText("测试注入声明（非真实模型答案）");
  await card.getByText("查看 SQL、证据与执行步骤", { exact: true }).click();
  await expect(card).toContainText("SUM(amount_cents)");
  await expect(card).toContainText("11000");
  await page.reload();
  await page.getByText("销售增长率验证 · Sprint 1", { exact: true }).click();
  await expect(page.getByRole("article", { name: "证据验证结果" })).toHaveCount(2);
  await expect(page.getByRole("article", { name: "证据验证结果" }).first()).toContainText("证据验证：失败");
});
