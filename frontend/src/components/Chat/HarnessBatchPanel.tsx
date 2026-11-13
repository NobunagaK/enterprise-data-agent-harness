import { useEffect, useRef, useState } from "react";
import { getHarnessRun, type HarnessRun } from "@/api/harness";
import {
  createHarnessBatch,
  getHarnessBatch,
  listHarnessBatches,
  type BatchCaseOutcome,
  type HarnessBatch,
} from "@/api/harnessBatches";
import { ValidationResultCard } from "./ValidationResultCard";

const RESULT_LABEL: Record<string, string> = {
  passed: "通过",
  failed: "失败",
  unverifiable: "无法验证",
  tool_error: "工具错误",
};

const CASE_STATE_LABEL: Record<string, string> = {
  completed: "已完成",
  timeout: "超时",
  error: "执行错误",
  cancelled: "已取消",
  skipped: "未执行",
  interrupted: "中断（结果未确认）",
};

const STOP_LABEL: Record<string, string> = {
  timed_out: "整批超时：已停止启动后续案例。",
  cancelled: "批次已取消：已保留完成结果。",
  interrupted: "批次中断：未完成案例的执行结果无法确认。",
};

export function BatchSummary({ batch }: { batch: HarnessBatch }) {
  const { counts } = batch;
  return (
    <div className="space-y-2" data-testid="batch-summary">
      {STOP_LABEL[batch.state] && <p role="status" className="text-xs text-amber-600">{STOP_LABEL[batch.state]}</p>}
      <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs">
        <span>完成 {counts.completed}/{counts.attempted}</span>
        <span>通过 {counts.passed}</span>
        <span>失败 {counts.failed}</span>
        <span>无法验证 {counts.unverifiable}</span>
        <span>工具错误 {counts.tool_error}</span>
        {(counts.timeout > 0 || counts.error > 0) && (
          <span className="text-amber-600">
            超时 {counts.timeout} · 执行错误 {counts.error}
          </span>
        )}
        {((counts.skipped ?? 0) > 0 || (counts.cancelled ?? 0) > 0 || (counts.interrupted ?? 0) > 0) && (
          <span className="text-amber-600">
            已尝试 {counts.attempted} · 未执行 {counts.skipped ?? 0} · 已取消 {counts.cancelled ?? 0} · 结果未确认 {counts.interrupted ?? 0}
          </span>
        )}
      </div>
      {batch.batch_timeout_s != null && (
        <p className="text-xs text-muted-foreground">
          整批预算 {batch.batch_timeout_s} 秒 · {batch.case_timeout_s == null ? "单例共用整批预算" : `单例预算 ${batch.case_timeout_s} 秒`}；结束前会等待正在清理的资源释放。
        </p>
      )}
      <ul className="space-y-1 text-xs">
        {batch.outcomes.map(outcome => (
          <li key={outcome.case_id} className="flex flex-wrap items-center gap-2">
            <span className="font-mono">{outcome.case_id}</span>
            <span>
              {CASE_STATE_LABEL[outcome.state]}
              {outcome.result_status ? ` · ${RESULT_LABEL[outcome.result_status]}` : ""}
            </span>
            {outcome.expected_status && outcome.matches_expected === false && (
              <span className="text-amber-600">
                （期望 {RESULT_LABEL[outcome.expected_status]}）
              </span>
            )}
            <span className="text-muted-foreground">{outcome.duration_ms} ms</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function HarnessBatchPanel({ conversationId }: { conversationId: string | null }) {
  const [batches, setBatches] = useState<HarnessBatch[]>([]);
  const [selected, setSelected] = useState<HarnessBatch | null>(null);
  const [detail, setDetail] = useState<HarnessRun | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const mounted = useRef(true);
  const pending = useRef(false);

  useEffect(() => {
    mounted.current = true;
    let active = true;
    listHarnessBatches(conversationId)
      .then(data => {
        if (active) {
          setBatches(data);
          setSelected(data[0] ?? null);
        }
      })
      .catch(() => {
        if (active) setError("批次历史读取失败，请检查后端及数据库迁移 007。");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
      mounted.current = false;
    };
  }, [conversationId]);

  async function execute() {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setError("");
    setDetail(null);
    try {
      const batch = await createHarnessBatch({ conversation_id: conversationId });
      if (mounted.current) {
        setBatches(previous => [batch, ...previous.filter(item => item.id !== batch.id)].slice(0, 20));
        setSelected(batch);
      }
    } catch (err) {
      if (mounted.current) setError(String(err));
    } finally {
      pending.current = false;
      if (mounted.current) setBusy(false);
    }
  }

  async function openCase(outcome: BatchCaseOutcome) {
    if (!outcome.run_id) return;
    setError("");
    try {
      const run = await getHarnessRun(outcome.run_id);
      if (mounted.current) setDetail(run);
    } catch (err) {
      if (mounted.current) setError(String(err));
    }
  }

  async function reload(batchId: string) {
    setError("");
    try {
      const batch = await getHarnessBatch(batchId);
      if (mounted.current) {
        setSelected(batch);
        setDetail(null);
      }
    } catch (err) {
      if (mounted.current) setError(String(err));
    }
  }

  return (
    <details className="border-t border-border px-4 py-2 shrink-0" data-print-hide>
      <summary className="cursor-pointer text-sm font-medium">批量评测 · Sprint 2</summary>
      <div className="space-y-3 mt-2 max-h-[45vh] overflow-y-auto">
        <p className="text-xs text-muted-foreground">
          运行服务端版本化的固定案例集（10 条：通过 / 失败 / 无法验证）。单条异常不会中断后续案例。
        </p>
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <button
            className="bg-primary text-primary-foreground rounded px-3 py-1 disabled:opacity-50"
            disabled={busy || loading}
            onClick={execute}
          >
            {busy ? "批量运行中…" : "运行批次"}
          </button>
          {selected && (
            <button
              className="border rounded px-2 py-1 text-xs"
              disabled={busy}
              onClick={() => reload(selected.id)}
            >
              刷新当前批次
            </button>
          )}
          {selected && (
            <span className="text-xs text-muted-foreground">
              批次 {selected.id.slice(0, 8)} · {selected.state}
            </span>
          )}
        </div>
        {error && (
          <p role="alert" className="text-red-500 text-sm">
            {error}
          </p>
        )}
        <div aria-live="polite" aria-busy={busy}>
          {selected ? (
            <>
              <BatchSummary batch={selected} />
              <ul className="mt-2 space-y-1 text-xs">
                {selected.outcomes.map(outcome => (
                  <li key={`open-${outcome.case_id}`}>
                    <button
                      className="underline disabled:no-underline disabled:opacity-50"
                      disabled={!outcome.run_id}
                      onClick={() => openCase(outcome)}
                    >
                      查看 {outcome.case_id}
                    </button>
                  </li>
                ))}
              </ul>
              {detail && (
                <div className="mt-2">
                  {selected.outcomes.some(outcome => outcome.run_id === detail.id && outcome.state !== "completed") && (
                    <p className="text-xs text-amber-600">本例未正常完成；下方为最后保存的运行快照，可能未包含中止前的全部步骤。</p>
                  )}
                  <ValidationResultCard run={detail} />
                </div>
              )}
            </>
          ) : (
            !busy && (
              <p className="text-xs text-muted-foreground">
                暂无批次记录。点击“运行批次”执行固定案例集。
              </p>
            )
          )}
          {batches.length > 1 && (
            <div className="mt-3 space-y-1 text-xs">
              <p className="text-muted-foreground">历史批次</p>
              {batches.slice(1).map(batch => (
                <button
                  key={batch.id}
                  className="block underline"
                  onClick={() => {
                    setSelected(batch);
                    setDetail(null);
                  }}
                >
                  {batch.started_at} · {batch.state} · {batch.counts.passed}/{batch.counts.attempted}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </details>
  );
}
