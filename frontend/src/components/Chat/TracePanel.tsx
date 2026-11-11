import type { HarnessEvidence, HarnessRun, HarnessStep } from "@/api/harness";
import { SqlMessage } from "./messages/SqlMessage";

const kinds: Record<HarnessStep["kind"], string> = {
  query: "SQL 查询", claim: "记录声明", validation: "证据验证", model: "模型调用",
  tool: "工具/配置", answer: "记录回答", context: "上下文",
};
const states: Record<HarnessStep["status"], string> = {
  running: "运行中", completed: "已完成", error: "失败", skipped: "已跳过",
};

function EvidenceView({ item, claimed }: { item: HarnessEvidence; claimed: boolean }) {
  return <details className="mt-2">
    <summary className="cursor-pointer">查看对应 SQL 与证据</summary>
    <p className="text-xs break-all">证据：{item.id}{claimed ? " · 声明引用的证据" : ""}</p>
    <p className="text-xs">数据：{item.dataset_version} · 金额单位：{item.amount_unit === "CNY_cent" ? "人民币分" : item.amount_unit}</p>
    <SqlMessage payload={item} />
  </details>;
}

export function TracePanel({ run }: { run: HarnessRun }) {
  const stepCounts = new Map<string, number>();
  for (const step of run.steps) stepCounts.set(step.id, (stepCounts.get(step.id) ?? 0) + 1);
  const queryIds = new Set(run.steps
    .filter(step => step.kind === "query" && stepCounts.get(step.id) === 1)
    .map(step => step.id));
  const evidence = run.evidence.filter(item => item.run_id === run.id);
  const excluded = run.evidence.length - evidence.length;
  const unlinked = evidence.filter(item => !queryIds.has(item.step_id));
  const references = run.claim ? evidence.filter(item => item.id === run.claim?.evidence_id) : [];
  const renderEvidence = (items: HarnessEvidence[]) => items.map((item, index) =>
    <EvidenceView key={`${item.id}-${index}`} item={item} claimed={references.length === 1 && references[0] === item} />);

  return <section aria-label="执行轨迹" className="space-y-3">
    <p className="text-xs break-all">运行 ID：{run.id}</p>
    {!run.steps.length && <p>未记录执行步骤</p>}
    {excluded > 0 && <p role="status">已排除 {excluded} 条不属于本次运行的证据。</p>}
    {run.claim && references.length === 0 && <p role="status">声明引用的证据缺失或不属于本次运行。</p>}
    {references.length > 1 && <p role="status">声明引用不唯一，无法确定对应证据。</p>}
    <ol className="space-y-2">
      {run.steps.map((step, index) => {
        const linked = queryIds.has(step.id) ? evidence.filter(item => item.step_id === step.id) : [];
        return <li key={`${step.id}-${index}`} className="border rounded p-2">
          <p>{index + 1}. {kinds[step.kind]} · {states[step.status]}</p>
          <p className="text-xs break-all">步骤 ID：{step.id}</p>
          {step.parent_step_id && <p className="text-xs break-all">{stepCounts.get(step.parent_step_id) === 1
            ? `父步骤：${step.parent_step_id}` : "父步骤缺失或不唯一"}</p>}
          <p>耗时：{step.duration_ms == null ? "耗时未记录" : `${step.duration_ms.toFixed(2)} ms`}</p>
          <p className="text-xs">{step.started_at ?? "开始时间不可用"} → {step.finished_at ?? "结束时间不可用"}</p>
          {step.error && <p role="status">错误码：{step.error}</p>}
          {step.kind === "model" && <p>输入 Token：{step.token_usage?.input_tokens ?? "不可用"} · 输出 Token：{step.token_usage?.output_tokens ?? "不可用"}</p>}
          {renderEvidence(linked)}
          {step.kind === "query" && linked.length === 0 && <p className="text-xs">未记录关联证据</p>}
        </li>;
      })}
    </ol>
    {unlinked.length > 0 && <div className="border rounded p-2">
      <p role="status">未能关联到唯一本次查询步骤的证据（仅供排查）</p>
      {renderEvidence(unlinked)}
    </div>}
  </section>;
}
