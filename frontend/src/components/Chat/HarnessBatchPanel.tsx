import { useEffect, useRef, useState } from "react";
import { getHarnessRun, type HarnessRun } from "@/api/harness";
import {
  createHarnessBatch,
  getHarnessBatch,
  listHarnessBatches,
  listHarnessCaseSets,
  type BatchCaseOutcome,
  type CaseSetSummary,
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
};

const RULE_LABEL: Record<string, string> = {
  growth_rate: "增长率",
  sales_total: "销售总额",
};

export function BatchSummary({ batch }: { batch: HarnessBatch }) {
  const { counts } = batch;
  return (
    <div className="space-y-2" data-testid="batch-summary">
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
      </div>
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
  const [caseSets, setCaseSets] = useState<CaseSetSummary[]>([]);
  const [caseSetId, setCaseSetId] = useState("sprint2-sales-v1");
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [catalogError, setCatalogError] = useState("");
  const [batches, setBatches] = useState<HarnessBatch[]>([]);
  const [selected, setSelected] = useState<HarnessBatch | null>(null);
  const [detail, setDetail] = useState<HarnessRun | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const mounted = useRef(true);
  const pending = useRef(false);

  useEffect(() => {
    let active = true;
    listHarnessCaseSets()
      .then(data => {
        if (active) {
          setCaseSets(data);
          setCaseSetId(current => data.some(item => item.case_set_id === current)
            ? current : (data[0]?.case_set_id ?? ""));
          if (!data.length) setCatalogError("暂无可运行的案例集。");
        }
      })
      .catch(() => {
        if (active) setCatalogError("案例集读取失败，请刷新页面重试。");
      })
      .finally(() => {
        if (active) setCatalogLoading(false);
      });
    return () => { active = false; };
  }, []);

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
    if (pending.current || !caseSets.some(item => item.case_set_id === caseSetId)) return;
    pending.current = true;
    setBusy(true);
    setError("");
    setDetail(null);
    try {
      const batch = await createHarnessBatch({
        case_set_id: caseSetId,
        conversation_id: conversationId,
      });
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

  const selectedCaseSet = caseSets.find(item => item.case_set_id === caseSetId);

  return (
    <details className="border-t border-border px-4 py-2 shrink-0" data-print-hide>
      <summary className="cursor-pointer text-sm font-medium">批量评测 · Sprint 2</summary>
      <div className="space-y-3 mt-2 max-h-[45vh] overflow-y-auto">
        <p className="text-xs text-muted-foreground">
          运行固定案例集，汇总通过、失败、无法验证及工具错误。单条异常不会中断后续案例。
        </p>
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <label>
            案例集
            <select
              aria-label="案例集"
              className="ml-2 rounded border bg-background px-2 py-1"
              value={caseSetId}
              disabled={busy || catalogLoading || !caseSets.length}
              onChange={event => setCaseSetId(event.target.value)}
            >
              {caseSets.map(item => (
                <option key={item.case_set_id} value={item.case_set_id}>
                  {item.rule_ids.map(rule => RULE_LABEL[rule] ?? rule).join(" + ")} · {item.case_count} 条
                </option>
              ))}
            </select>
          </label>
          <button
            className="bg-primary text-primary-foreground rounded px-3 py-1 disabled:opacity-50"
            disabled={busy || loading || catalogLoading || !selectedCaseSet}
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
              批次 {selected.id.slice(0, 8)} · {selected.state} · {selected.case_set_id} v{selected.case_set_version}
            </span>
          )}
        </div>
        {selectedCaseSet && (
          <p className="text-xs text-muted-foreground">
            {selectedCaseSet.sources.map(source => source === "test_injected"
              ? "固定测试声明（非真实模型输出）" : "真实模型声明").join(" / ")}
            {" · "}{selectedCaseSet.case_count} 条 · 数据集 {selectedCaseSet.dataset_version}
          </p>
        )}
        {catalogError && <p role="alert" className="text-red-500 text-sm">{catalogError}</p>}
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
                  {batch.started_at} · {batch.case_set_id} v{batch.case_set_version} · {batch.state} · {batch.counts.passed}/{batch.counts.attempted}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </details>
  );
}
