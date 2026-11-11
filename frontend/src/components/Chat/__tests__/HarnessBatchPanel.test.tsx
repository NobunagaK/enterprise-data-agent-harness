import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { HarnessBatch } from "@/api/harnessBatches";
import { BatchSummary } from "../HarnessBatchPanel";

const counts = {
  attempted: 3,
  completed: 2,
  passed: 1,
  failed: 1,
  unverifiable: 0,
  tool_error: 0,
  timeout: 1,
  error: 0,
};

const batch: HarnessBatch = {
  schema_version: 1,
  id: "batch-fixture",
  case_set_id: "sprint2-sales-v1",
  case_set_version: "1",
  conversation_id: null,
  state: "partial",
  started_at: "2026-11-07T00:00:00Z",
  finished_at: "2026-11-07T00:00:02Z",
  counts,
  outcomes: [
    {
      case_id: "growth-exact",
      state: "completed",
      run_id: "run-1",
      result_status: "passed",
      reason: "within_tolerance",
      expected_status: "passed",
      matches_expected: true,
      duration_ms: 12,
    },
    {
      case_id: "growth-wrong",
      state: "completed",
      run_id: "run-2",
      result_status: "failed",
      reason: "outside_tolerance",
      expected_status: "failed",
      matches_expected: true,
      duration_ms: 9,
    },
    {
      case_id: "growth-timeout",
      state: "timeout",
      run_id: null,
      result_status: null,
      reason: "case_timeout",
      expected_status: "passed",
      matches_expected: null,
      duration_ms: 500,
    },
  ],
};

describe("batch summary rendering", () => {
  it("shows the four outcome categories and the attempted total", () => {
    const html = renderToStaticMarkup(<BatchSummary batch={batch} />);
    expect(html).toContain("完成 2/3");
    expect(html).toContain("通过 1");
    expect(html).toContain("失败 1");
    expect(html).toContain("无法验证 0");
    expect(html).toContain("工具错误 0");
    expect(html).toContain("超时 1");
  });

  it("marks a timeout as a case state, never as a passing result", () => {
    const html = renderToStaticMarkup(<BatchSummary batch={batch} />);
    expect(html).toContain("growth-timeout");
    expect(html).toContain("超时");
    expect(html).not.toContain("growth-timeout通过");
  });

  it("flags an expected-status mismatch without hiding the actual result", () => {
    const mismatched: HarnessBatch = {
      ...batch,
      outcomes: [
        {
          ...batch.outcomes[0],
          case_id: "growth-mismatch",
          result_status: "passed",
          expected_status: "failed",
          matches_expected: false,
        },
      ],
    };
    const html = renderToStaticMarkup(<BatchSummary batch={mismatched} />);
    expect(html).toContain("已完成 · 通过");
    expect(html).toContain("期望 失败");
  });
});
