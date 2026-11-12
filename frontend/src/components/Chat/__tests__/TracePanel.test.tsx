import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { HarnessRun } from "@/api/harness";
import { TracePanel } from "../TracePanel";
import { ValidationResultCard } from "../ValidationResultCard";

// Synthetic association fixtures; these are not recorded model/human results.
const base: HarnessRun = {
  schema_version: 2, id: "run-a", conversation_id: null, rule_id: "growth_rate",
  source: "test_injected", state: "completed",
  started_at: "2026-11-12T00:00:00Z", finished_at: "2026-11-12T00:00:01Z",
  model: null, answer: null, answer_truncated: false,
  steps: [{ id: "query-a", kind: "query", status: "completed", duration_ms: 2, error: null }],
  evidence: [{ id: "e-a", run_id: "run-a", step_id: "query-a", sql: "SELECT 11000 AS amount_cents",
    columns: ["amount_cents"], rows: [{ amount_cents: 11000 }], truncated: false,
    dataset_version: "sales-v1", amount_unit: "CNY_cent" }],
  claim: { evidence_id: "e-a", claimed_value: "18.7", unit: "percent" },
  result: { status: "failed", reason: "outside_tolerance", rule_version: "growth_rate-v2",
    tolerance_pp: "0.01", difference_pp: "8.7", expected_value: "10", expected_display: "10.00", claimed_value: "18.7" },
};

function panel(run: HarnessRun) { return renderToStaticMarkup(<TracePanel run={run} />); }
function card(run: HarnessRun) { return renderToStaticMarkup(<ValidationResultCard run={run} />); }

describe("trace evidence association", () => {
  it("renders valid SQL once across the whole result card", () => {
    const html = card(base);
    expect(html.match(/SELECT 11000 AS amount_cents/g)).toHaveLength(1);
    expect(html).toContain("声明引用的证据");
    expect(html.match(/运行 ID：/g)).toHaveLength(1);
  });
  it("never renders a different run's evidence, even with a matching step id", () => {
    const foreign = { ...base.evidence[0], id: "foreign", run_id: "run-b", sql: "foreign-secret-sql" };
    const html = card({ ...base, evidence: [...base.evidence, foreign] });
    expect(html).not.toContain("foreign-secret-sql");
    expect(html).toContain("已排除 1 条不属于本次运行的证据");
  });
  it("shows same-run orphan evidence with an explicit missing association", () => {
    const html = card({ ...base, evidence: [{ ...base.evidence[0], step_id: "missing" }] });
    expect(html).toContain("未能关联到唯一本次查询步骤的证据");
    expect(html.match(/SELECT 11000 AS amount_cents/g)).toHaveLength(1);
  });
  it("does not attach evidence to a non-query step", () => {
    const html = panel({ ...base, steps: [{ ...base.steps[0], kind: "model" }] });
    expect(html).toContain("未能关联到唯一本次查询步骤的证据");
  });
  it("does not duplicate evidence under ambiguous step identifiers", () => {
    const html = panel({ ...base, steps: [base.steps[0], base.steps[0]] });
    expect(html).toContain("未能关联到唯一本次查询步骤的证据");
    expect(html.match(/SELECT 11000 AS amount_cents/g)).toHaveLength(1);
  });
  it("marks a missing claim reference without assigning another evidence", () => {
    const html = panel({ ...base, claim: { ...base.claim!, evidence_id: "absent" } });
    expect(html).toContain("声明引用的证据缺失或不属于本次运行");
    expect(html).not.toContain("声明引用的证据</");
  });
  it("marks ambiguous claim references", () => {
    const html = panel({ ...base, evidence: [base.evidence[0], base.evidence[0]] });
    expect(html).toContain("声明引用不唯一，无法确定对应证据");
  });
  it("retains evidence when legacy reports have no steps", () => {
    const html = panel({ ...base, steps: [] });
    expect(html).toContain("未记录执行步骤");
    expect(html).toContain("SELECT 11000 AS amount_cents");
  });
});

describe("trace measurements and status", () => {
  it("preserves unknown timing and token usage", () => {
    const html = panel({ ...base, evidence: [], claim: null,
      steps: [{ id: "model", kind: "model", status: "completed", duration_ms: null, error: null }] });
    expect(html).toContain("耗时未记录");
    expect(html).toContain("开始时间不可用");
    expect(html).toContain("输入 Token：不可用");
    expect(html).not.toContain("0.00 ms");
  });
  it("renders measured zero separately from unknown", () => {
    const html = panel({ ...base, evidence: [], claim: null,
      steps: [{ id: "model", kind: "model", status: "completed", duration_ms: 0, error: null,
        token_usage: { input_tokens: 0, output_tokens: null } }] });
    expect(html).toContain("0.00 ms");
    expect(html).toContain("输入 Token：0");
    expect(html).toContain("输出 Token：不可用");
  });
  it("shows safe error codes and terminal status", () => {
    const html = panel({ ...base, evidence: [], claim: null,
      steps: [{ id: "setup", kind: "tool", status: "error", duration_ms: 1, error: "model_configuration_error" }] });
    expect(html).toContain("失败");
    expect(html).toContain("错误码：model_configuration_error");
  });
  it("keeps running and skipped distinct", () => {
    const html = panel({ ...base, evidence: [], claim: null, steps: [
      { id: "q", kind: "query", status: "running", duration_ms: null, error: null },
      { id: "v", kind: "validation", status: "skipped", duration_ms: null, error: null },
    ] });
    expect(html).toContain("运行中");
    expect(html).toContain("已跳过");
  });
  it("shows parent identity only when the parent exists in this run", () => {
    const html = panel({ ...base, evidence: [], claim: null, steps: [
      base.steps[0], { ...base.steps[0], id: "child", parent_step_id: "query-a" },
      { ...base.steps[0], id: "orphan", parent_step_id: "absent" },
    ] });
    expect(html).toContain("父步骤：query-a");
    expect(html).toContain("父步骤缺失或不唯一");
  });
  it("preserves source labels, cents and real evidence units", () => {
    const html = card({ ...base, rule_id: "sales_total", claim: { ...base.claim!, unit: "CNY_cent", claimed_value: "11001" },
      result: { ...base.result!, unit: "CNY_cent", rule_version: "sales_total-v1", tolerance: "0", difference: "1",
        tolerance_pp: null, difference_pp: null, expected_value: "11000", expected_display: "11000" } });
    expect(html).toContain("计算结果：11000 分");
    expect(html).toContain("测试注入声明（非真实模型答案）");
    expect(html).not.toContain("个百分点");
    expect(html).toContain("金额单位：人民币分");
    expect(panel({ ...base, evidence: [{ ...base.evidence[0], amount_unit: "USD_cent" }] })).toContain("金额单位：USD_cent");
  });
});
