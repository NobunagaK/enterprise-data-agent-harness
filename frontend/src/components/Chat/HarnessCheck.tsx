import { useEffect, useRef, useState } from "react";
import { createHarnessRun, listHarnessRuns, type HarnessRun } from "@/api/harness";
import { ValidationResultCard } from "./ValidationResultCard";

export function HarnessCheck({ conversationId }: { conversationId: string | null }) {
  const [runs, setRuns] = useState<HarnessRun[]>([]);
  const [value, setValue] = useState("10");
  const [source, setSource] = useState<HarnessRun["source"]>("test_injected");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const mounted = useRef(true);
  const pending = useRef(false);
  useEffect(() => {
    mounted.current = true;
    let active = true;
    listHarnessRuns(conversationId)
      .then(data => { if (active) setRuns(data); })
      .catch(() => { if (active) setError("历史记录读取失败，请检查后端及数据库迁移。"); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; mounted.current = false; };
  }, [conversationId]);

  async function execute() {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setError("");
    try {
      const run = await createHarnessRun(conversationId, source, value);
      if (mounted.current) setRuns(previous => [run, ...previous.filter(r => r.id !== run.id)].slice(0, 20));
    } catch (err) {
      if (mounted.current) setError(String(err));
    } finally {
      pending.current = false;
      if (mounted.current) setBusy(false);
    }
  }

  return (
    <details className="border-t border-border px-4 py-2 shrink-0" data-print-hide>
      <summary className="cursor-pointer text-sm font-medium">销售增长率验证 · Sprint 1</summary>
      <div className="space-y-3 mt-2 max-h-[45vh] overflow-y-auto">
        <p className="text-xs text-muted-foreground">
          固定合成数据：demo-store，2024 年 100 元、2025 年 110 元。本入口单独运行验证案例，不验证普通聊天中的任意答案。
        </p>
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <label>声明来源 <select aria-label="声明来源" className="bg-background border rounded p-1" value={source} disabled={busy}
            onChange={event => setSource(event.target.value as HarnessRun["source"])}>
            <option value="test_injected">固定测试声明（无需模型）</option>
            <option value="agent_generated">真实模型（需先在 Settings 配置，可能产生费用）</option>
          </select></label>
          {source === "test_injected" && <label>声明增长率（%） <input aria-label="声明增长率" className="bg-background border rounded p-1 w-24"
            value={value} maxLength={64} disabled={busy} onChange={event => setValue(event.target.value)} /></label>}
          <button className="bg-primary text-primary-foreground rounded px-3 py-1 disabled:opacity-50" disabled={busy || loading} onClick={execute}>
            {busy ? "运行中…" : "运行验证"}
          </button>
        </div>
        {error && <p role="alert" className="text-red-500 text-sm">{error}</p>}
        <div aria-live="polite" aria-busy={busy} className="space-y-2">
          {runs.map(run => <ValidationResultCard key={run.id} run={run} />)}
          {!runs.length && !busy && <p className="text-xs text-muted-foreground">暂无运行记录。输入 10 或 18.7 可分别检查通过和失败案例。</p>}
        </div>
      </div>
    </details>
  );
}
