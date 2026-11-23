import { expect, test } from "@playwright/test";

test("a delayed history response cannot replace the selected conversation's messages", async ({ page }) => {
  const summaries = ["history-a", "history-b"].map(id => ({
    id, title: id, engine_name: "", message_count: 1,
    created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z",
  }));
  const contents = ["First conversation transcript", "Selected conversation transcript"];
  await page.addInitScript(() => localStorage.setItem("onboarding_dismissed", "1"));
  await page.route("**/api/conversations", route => route.fulfill({ json: summaries }));

  let releaseFirst!: () => void;
  const firstMayFinish = new Promise<void>(resolve => { releaseFirst = resolve; });
  for (const [index, conversation] of summaries.entries()) {
    await page.route(`**/api/conversations/${conversation.id}`, async route => {
      if (index === 0) await firstMayFinish;
      await route.fulfill({ json: {
        ...conversation, is_streaming: false,
        messages: [{
          id: `${conversation.id}-msg`, event_type: "TEXT", role: "user",
          payload: { text: contents[index] }, created_at: conversation.created_at,
        }],
      } });
    });
  }

  await page.goto("/");
  const firstRequested = page.waitForRequest("**/api/conversations/history-a");
  await page.locator('[data-conv-id="history-a"]').click();
  await firstRequested;
  await page.locator('[data-conv-id="history-b"]').click();
  await expect(page.getByText(contents[1], { exact: true })).toBeVisible();

  const firstFinished = page.waitForEvent("requestfinished", req => req.url().endsWith("/api/conversations/history-a"));
  releaseFirst();
  await firstFinished;
  // Let the fetch continuation update React and paint before checking the transcript.
  await page.evaluate(() => new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
  await expect(page.getByText(contents[0], { exact: true })).toHaveCount(0);
  await expect(page.getByText(contents[1], { exact: true })).toBeVisible();
});
