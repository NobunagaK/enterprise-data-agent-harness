import { expect, test } from "@playwright/test";

for (const rule of ["growth_rate", "sales_total"] as const) {
  test(`${rule}: persisted failure opens the correct SQL trace after reload`, async ({ page }) => {
    await page.addInitScript(() => localStorage.setItem("onboarding_dismissed", "1"));
    await page.route("**/api/greeting*", route => route.fulfill({ json: { greeting: "" } }));
    await page.route("**/api/version", route => route.fulfill({ json: { current_version: "test", update_available: false } }));
    await page.goto("/");
    await page.getByText("销售证据验证 · Sprint 2", { exact: true }).click();
    await page.getByLabel("验证规则", { exact: true }).selectOption(rule);
    await page.getByLabel(rule === "sales_total" ? "声明总额" : "声明增长率", { exact: true }).fill(rule === "sales_total" ? "11001" : "18.7");
    const submitted = page.waitForResponse(response => response.url().endsWith("/api/harness/runs") && response.request().method() === "POST");
    await page.getByRole("button", { name: "运行验证", exact: true }).click();
    const report = await (await submitted).json();
    expect(report.result.status).toBe("failed");
    expect(report.rule_id).toBe(rule);
    expect(report.steps.map((step: { kind: string }) => step.kind)).toEqual(["query", "claim", "validation"]);
    expect(report.steps.every((step: { status: string; started_at: string; finished_at: string; duration_ms: number }) =>
      step.status === "completed" && step.started_at && step.finished_at && step.duration_ms >= 0)).toBeTruthy();
    expect(report.claim.evidence_id).toBe(report.evidence[0].id);
    expect(report.evidence[0].step_id).toBe(report.steps[0].id);

    for (const reload of [false, true]) {
      if (reload) {
        await page.reload();
        await page.getByText("销售证据验证 · Sprint 2", { exact: true }).click();
      }
      const card = page.getByRole("article", { name: "证据验证结果" }).first();
      await expect(card).toContainText("证据验证：失败");
      await expect(card).toContainText(rule === "sales_total" ? "差值：1 分" : "差值：8.7 个百分点");
      await card.getByText("查看 SQL、证据与执行步骤", { exact: true }).click();
      const trace = card.getByRole("region", { name: "执行轨迹" });
      await expect(trace).toContainText(report.id);
      await expect(trace.getByRole("listitem")).toHaveCount(3);
      await expect(trace).toContainText("SQL 查询 · 已完成");
      await expect(trace).toContainText("记录声明 · 已完成");
      await expect(trace).toContainText("证据验证 · 已完成");
      await trace.getByText("查看对应 SQL 与证据", { exact: true }).click();
      await expect(trace).toContainText("声明引用的证据");
      await expect(trace).toContainText(report.evidence[0].id);
      await expect(trace.locator("pre")).toHaveCount(1);
      await expect(trace.locator("pre")).toHaveText(report.evidence[0].sql);
      await expect(trace.getByRole("table")).toBeVisible();
      await expect(trace).not.toContainText("时间不可用");
    }
  });
}

test("synthetic configuration-error snapshot shows a failure step without invented tokens", async ({ page }) => {
  // UI fixture only. Backend setup failure is exercised separately with local doubles.
  const fixture = {
    id: "configuration-error-ui-fixture", conversation_id: null, source: "agent_generated",
    rule_id: "sales_total", state: "error", started_at: "2026-11-12T00:00:00Z", finished_at: "2026-11-12T00:00:01Z",
    model: null, answer: null, answer_truncated: false, claim: null, evidence: [],
    steps: [{ id: "setup-fixture", kind: "tool", status: "error", duration_ms: 1,
      started_at: "2026-11-12T00:00:00Z", finished_at: "2026-11-12T00:00:01Z", error: "model_configuration_error" }],
    result: { status: "tool_error", reason: "model_configuration_error", rule_version: "sales_total-v1",
      unit: "CNY_cent", tolerance: "0", difference: null, tolerance_pp: null, difference_pp: null,
      expected_value: null, expected_display: null, claimed_value: null },
  };
  await page.addInitScript(() => localStorage.setItem("onboarding_dismissed", "1"));
  await page.route("**/api/harness/runs", route => route.fulfill({ json: [fixture] }));
  await page.goto("/");
  await page.getByText("销售证据验证 · Sprint 2", { exact: true }).click();
  const card = page.getByRole("article", { name: "证据验证结果" }).first();
  await expect(card).toContainText("证据验证：工具错误");
  await expect(card).toContainText("模型配置或初始化失败");
  await card.getByText("查看 SQL、证据与执行步骤", { exact: true }).click();
  const trace = card.getByRole("region", { name: "执行轨迹" });
  await expect(trace).toContainText("工具/配置 · 失败");
  await expect(trace).toContainText("错误码：model_configuration_error");
  await expect(trace).not.toContainText("模型调用");
  await expect(trace).not.toContainText("Token");
  await expect(trace.getByText("查看对应 SQL 与证据", { exact: true })).toHaveCount(0);
});
