import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { HarnessRun } from "@/api/harness";
import { ValidationResultCard } from "../ValidationResultCard";

// Synthetic compatibility fixture, not an actual historical acceptance report.
const legacy: HarnessRun = {
  id: "legacy-fixture", conversation_id: null, source: "test_injected",
  started_at: "2026-10-30T00:00:00Z", finished_at: "2026-10-30T00:00:01Z",
  state: "completed", model: null, answer: null, answer_truncated: false,
  steps: [{ id: "query", kind: "query", status: "completed", duration_ms: 1, error: null }],
  evidence: [],
  claim: { evidence_id: "e", claimed_value: "10", unit: "percent" },
  result: {
    status: "passed", reason: "within_tolerance", rule_version: "growth_rate-v2",
    tolerance_pp: "0.01", expected_value: "10", expected_display: "10.00",
    claimed_value: "10", difference_pp: "0",
  },
};

describe("report contract rendering", () => {
  it("renders a Sprint 1 report without new fields", () => {
    const html = renderToStaticMarkup(<ValidationResultCard run={legacy} />);
    expect(html).toContain("计算结果：10.00%");
    expect(html).toContain("容差：0.01 个百分点");
    expect(html).toContain("测试注入声明（非真实模型答案）");
  });
  it("renders amount results in cents without percentage aliases", () => {
    const run: HarnessRun = {
      ...legacy,
      schema_version: 2,
      rule_id: "sales_total",
      claim: { evidence_id: "e", claimed_value: "11001", unit: "CNY_cent" },
      result: {
        status: "failed", reason: "outside_tolerance", rule_version: "sales_total-v1",
        unit: "CNY_cent", tolerance: "0", difference: "1", tolerance_pp: null,
        difference_pp: null, expected_value: "11000", expected_display: "11000", claimed_value: "11001",
      },
    };
    const html = renderToStaticMarkup(<ValidationResultCard run={run} />);
    expect(html).toContain("计算结果：11000 分");
    expect(html).toContain("差值：1 分");
    expect(html).toContain("容差：0 分");
    expect(html).not.toContain("个百分点");
    expect(html).not.toContain("11000%");
  });
  it("does not turn unavailable timing into a measured zero", () => {
    const run: HarnessRun = { ...legacy, steps: [{
      id: "model-step", kind: "model", status: "running", duration_ms: null, error: null,
    }] };
    const html = renderToStaticMarkup(<ValidationResultCard run={run} />);
    expect(html).toContain("耗时未记录");
    expect(html).not.toContain("0.00 ms");
  });
});
