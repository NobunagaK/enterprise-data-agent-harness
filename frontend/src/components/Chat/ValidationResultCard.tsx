import type { HarnessRun } from "@/api/harness";
import { SqlMessage } from "./messages/SqlMessage";

const labels = { passed: "通过", failed: "失败", unverifiable: "无法验证", tool_error: "工具错误" };
const reasons: Record<string, string> = {
  within_tolerance: "声明值与查询证据一致，处于约定容差内。",
  outside_tolerance: "声明值与查询证据不一致，超出约定容差。",
  missing_claim: "未获得有效的结构化声明，不能判定通过。",
  zero_denominator: "上期销售额为零，普通同比公式不适用。",
  evidence_not_found_or_wrong_run: "证据不存在，或不属于本次运行。",
  truncated_evidence: "查询证据被截断，无法完整验证。",
  execution_error: "执行失败；请检查模型配置或服务状态。",
  query_failed: "查询执行失败。",
  validator_error: "验证器发生内部错误。",
  run_timeout: "运行超过 60 秒限制。",
};

export function ValidationResultCard({ run }: { run: HarnessRun }) {
  const result = run.result;
  return (
    <article className="rounded-lg border border-border p-3 space-y-2 text-sm" aria-label="证据验证结果">
      <div className="font-medium">证据验证：{result ? labels[result.status] : "未完成"}</div>
      <p className="text-xs text-muted-foreground">
        {run.source === "test_injected" ? "测试注入声明（非真实模型答案）" : "模型生成声明"}
        {run.model ? ` · ${run.model}` : ""}
      </p>
      <p>声明：{run.claim ? `${run.claim.claimed_value} ${run.claim.unit}` : "未提交"}
        {result?.expected_display != null && ` · 计算结果：${result.expected_display}%`}</p>
      {run.answer && <p className="whitespace-pre-wrap">模型回答：{run.answer}{run.answer_truncated ? "（已截断）" : ""}</p>}
      <p>{result ? (reasons[result.reason] ?? result.reason) : "记录尚未完成。刷新历史可检查状态；进程中断的运行不会计为通过。"}</p>
      {result && <p className="text-xs text-muted-foreground">容差：{result.tolerance_pp} 个百分点 · 规则：{result.rule_version}</p>}
      <details>
        <summary className="cursor-pointer">查看 SQL、证据与执行步骤</summary>
        <div className="mt-2 space-y-3">
          <p className="text-xs break-all">运行 ID：{run.id}</p>
          <p className="text-xs">{run.started_at} → {run.finished_at ?? "尚未结束"}</p>
          {run.steps.map(step => <p key={step.id} className="text-xs">
            {step.kind} · {step.status} · {step.duration_ms.toFixed(2)} ms {step.error ?? ""}
          </p>)}
          {run.evidence.map(item => <div key={item.id} className="space-y-1">
            <p className="text-xs break-all">证据：{item.id} · 数据：{item.dataset_version} · 金额单位：人民币分</p>
            <SqlMessage payload={item} />
          </div>)}
          <pre className="text-xs overflow-auto max-h-48">{JSON.stringify(result, null, 2)}</pre>
        </div>
      </details>
    </article>
  );
}
