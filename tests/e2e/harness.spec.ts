import { expect, test } from "@playwright/test";

test("fixed SQL evidence, failed claim and history survive page reload", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("onboarding_dismissed", "1"));
  // Isolate unrelated greeting/release lookups. Harness HTTP and SQL remain real.
  await page.route("**/api/greeting*", route => route.fulfill({ json: { greeting: "" } }));
  await page.route("**/api/version", route => route.fulfill({ json: { current_version: "test", update_available: false } }));
  await page.goto("/");
  await page.getByText("销售证据验证 · Sprint 2", { exact: true }).click();
  await page.getByRole("button", { name: "运行验证" }).click();
  // Batch runs share the same run list, so assert on the newest card only.
  await expect(page.getByText("证据验证：通过", { exact: true }).first()).toBeVisible();
  await page.getByLabel("声明增长率", { exact: true }).fill("18.7");
  await page.getByRole("button", { name: "运行验证" }).click();
  const card = page.getByRole("article", { name: "证据验证结果" }).first();
  await expect(card).toContainText("证据验证：失败");
  await expect(card).toContainText("计算结果：10.00%");
  await expect(card).toContainText("差值：8.7 个百分点");
  await expect(card).toContainText("容差：0.01 个百分点");
  await expect(card).toContainText("测试注入声明（非真实模型答案）");
  await card.getByText("查看 SQL、证据与执行步骤", { exact: true }).click();
  await expect(card).toContainText("SUM(amount_cents)");
  await expect(card).toContainText("11000");
  await page.reload();
  await page.getByText("销售证据验证 · Sprint 2", { exact: true }).click();
  const cards = page.getByRole("article", { name: "证据验证结果" });
  await expect(cards.first()).toContainText("证据验证：失败");
  await expect(cards.nth(1)).toContainText("证据验证：通过");
});

test("total validation uses cents, real SQL and persistent failure evidence", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("onboarding_dismissed", "1"));
  await page.route("**/api/greeting*", route => route.fulfill({ json: { greeting: "" } }));
  await page.route("**/api/version", route => route.fulfill({ json: { current_version: "test", update_available: false } }));
  await page.goto("/");
  await page.getByText("销售证据验证 · Sprint 2", { exact: true }).click();
  await page.getByLabel("验证规则", { exact: true }).selectOption("sales_total");
  await expect(page.getByLabel("声明总额", { exact: true })).toHaveValue("11000");
  await page.getByRole("button", { name: "运行验证", exact: true }).click();
  const card = page.getByRole("article", { name: "证据验证结果" }).first();
  await expect(card).toContainText("证据验证：通过");
  await expect(card).toContainText("计算结果：11000 分");
  await expect(card).toContainText("容差：0 分");
  await expect(card).not.toContainText("个百分点");

  await page.getByLabel("声明总额", { exact: true }).fill("11001");
  await page.getByRole("button", { name: "运行验证", exact: true }).click();
  await expect(card).toContainText("证据验证：失败");
  await expect(card).toContainText("差值：1 分");
  await expect(card).toContainText("测试注入声明（非真实模型答案）");
  await card.getByText("查看 SQL、证据与执行步骤", { exact: true }).click();
  await expect(card).toContainText("SUM(amount_cents)");
  await expect(card).toContainText("year = 2025");
  await expect(card).toContainText("sales_total-v1");

  await page.getByLabel("声明总额", { exact: true }).fill("11000.1");
  await page.getByRole("button", { name: "运行验证", exact: true }).click();
  await expect(card).toContainText("证据验证：无法验证");
  await expect(card).toContainText("总额声明必须为整数分");
  await page.reload();
  await page.getByText("销售证据验证 · Sprint 2", { exact: true }).click();
  const cards = page.getByRole("article", { name: "证据验证结果" });
  await expect(cards.first()).toContainText("证据验证：无法验证");
  await expect(cards.nth(1)).toContainText("证据验证：失败");
  await expect(cards.nth(1)).toContainText("差值：1 分");
  await expect(cards.nth(2)).toContainText("证据验证：通过");

  // Returning to the original rule must send percentage units again.
  await page.getByRole("button", { name: "运行验证", exact: true }).click();
  await expect(card).toContainText("计算结果：10.00%");
  await expect(card).toContainText("容差：0.01 个百分点");
});
