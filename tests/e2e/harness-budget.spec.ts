import { expect, test } from "@playwright/test";

test("expired persisted batch shows unconfirmed and unexecuted cases", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("onboarding_dismissed", "1"));
  await page.route("**/api/greeting*", route => route.fulfill({ json: { greeting: "" } }));
  const expired = {
    schema_version: 2, id: "interrupted-fixture", case_set_id: "sprint2-sales-v1",
    case_set_version: "1", conversation_id: null, state: "interrupted",
    started_at: "2026-11-12T00:00:00Z", finished_at: null,
    stop_reason: "execution_unconfirmed", batch_timeout_s: 300, case_timeout_s: 60,
    counts: { attempted: 1, completed: 0, passed: 0, failed: 0, unverifiable: 0,
      tool_error: 0, timeout: 0, error: 0, interrupted: 1, skipped: 1 },
    outcomes: [
      { case_id: "unknown", state: "interrupted", run_id: null, result_status: null,
        reason: "execution_unconfirmed", expected_status: null, matches_expected: null, duration_ms: 0 },
      { case_id: "never-started", state: "skipped", run_id: null, result_status: null,
        reason: "execution_unconfirmed", expected_status: null, matches_expected: null, duration_ms: 0 },
    ],
  };
  await page.route("**/api/harness/batches", route => route.fulfill({ json: [expired] }));
  await page.goto("/");
  await page.getByText("批量评测 · Sprint 2", { exact: true }).click();
  const summary = page.getByTestId("batch-summary");
  await expect(summary).toContainText("批次中断：未完成案例的执行结果无法确认。");
  await expect(summary).toContainText("已尝试 1 · 未执行 1");
  await expect(summary).toContainText("结果未确认 1");
  await expect(page.getByRole("button", { name: "查看 never-started" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "查看 unknown" })).toBeDisabled();
  await page.reload();
  await page.getByText("批量评测 · Sprint 2", { exact: true }).click();
  await expect(page.getByTestId("batch-summary")).toContainText("批次中断");
});
