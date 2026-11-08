import type { HarnessRun } from "@/api/harness";
import { SqlMessage } from "./messages/SqlMessage";

export function TracePanel({ run }: { run: HarnessRun }) {
  return <section aria-label="执行轨迹" className="space-y-3">
    <p className="text-xs break-all">运行 ID：{run.id}</p>
    {!run.steps.length && <p>未记录执行步骤</p>}
    <ol className="space-y-2">
      {run.steps.map((step, index) => <li key={step.id} className="border rounded p-2">
        <p>{index + 1}. {step.kind} · {step.status}</p>
        <p>耗时：{step.duration_ms == null ? "耗时未记录" : `${step.duration_ms.toFixed(2)} ms`}</p>
        <p className="text-xs">{step.started_at ?? "开始时间不可用"} → {step.finished_at ?? "结束时间不可用"}</p>
        {step.error && <p role="status">错误码：{step.error}</p>}
        {step.kind === "model" && <p>输入 Token：{step.token_usage?.input_tokens ?? "不可用"} · 输出 Token：{step.token_usage?.output_tokens ?? "不可用"}</p>}
        {run.evidence.filter(item => item.step_id === step.id && item.run_id === run.id).map(item =>
          <details key={item.id}><summary>查看对应 SQL 与证据</summary><p className="break-all">{item.id}</p><SqlMessage payload={item} /></details>)}
      </li>)}
    </ol>
  </section>;
}
