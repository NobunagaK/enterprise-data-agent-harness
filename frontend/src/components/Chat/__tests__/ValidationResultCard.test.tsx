import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { HarnessRun } from "@/api/harness";
import legacyFixture from "../../../../../tests/fixtures/harness/sprint1-run.json";
import { ValidationResultCard } from "../ValidationResultCard";

// Synthetic compatibility fixture, not an actual historical acceptance report.
const legacy = legacyFixture as HarnessRun;

describe("report contract rendering", () => {
  it("renders a Sprint 1 report without new fields", () => {
    const html = renderToStaticMarkup(<ValidationResultCard run={legacy} />);
    expect(html).toContain("计算结果：10.00%");
    expect(html).toContain("容差：0.01 个百分点");
    expect(html).toContain("测试注入声明（非真实模型答案）");
  });
  it("renders reserved amount result units without claiming the rule is executable", () => {
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
