export type HarnessSource = "test_injected" | "agent_generated";
export type ValidationStatus = "passed" | "failed" | "unverifiable" | "tool_error";
export type ValueUnit = "percent" | "CNY_cent";

// Only currently executable capabilities belong in this request type.
interface CommonRunRequest {
  source?: HarnessSource;
  claimed_value?: string;
  conversation_id?: string | null;
  case_id?: string | null;
  dataset_version?: "sales-v1";
}

export interface GrowthRunRequest extends CommonRunRequest {
  rule_id?: "growth_rate";
  unit?: "percent";
  parameters?: {
    store_id?: "demo-store";
    previous_year?: 2024;
    current_year?: 2025;
  };
}

export interface SalesTotalRunRequest extends CommonRunRequest {
  rule_id: "sales_total";
  unit?: "CNY_cent";
  parameters?: { store_id?: "demo-store"; year?: 2025 };
}

export type HarnessRunRequest = GrowthRunRequest | SalesTotalRunRequest;

export interface HarnessStep {
  id: string;
  kind: "query" | "claim" | "validation" | "model" | "tool" | "answer" | "context";
  status: "running" | "completed" | "error" | "skipped";
  duration_ms: number | null;
  error: string | null;
  parent_step_id?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  token_usage?: { input_tokens: number | null; output_tokens: number | null } | null;
}

export interface HarnessEvidence {
  id: string; run_id: string; step_id: string; sql: string;
  columns: string[]; rows: Record<string, unknown>[]; truncated: boolean;
  dataset_version: string; amount_unit: string;
}

export interface HarnessValidationResult {
  status: ValidationStatus;
  reason: string;
  rule_version: string;
  // Optional additive fields allow rendering original Sprint 1 snapshots.
  unit?: ValueUnit;
  tolerance?: string | null;
  difference?: string | null;
  tolerance_pp: string | null;
  expected_value: string | null;
  expected_display: string | null;
  claimed_value: string | null;
  difference_pp: string | null;
}

export interface HarnessRun {
  schema_version?: 1 | 2;
  id: string;
  conversation_id: string | null;
  case_id?: string | null;
  rule_id?: "growth_rate" | "sales_total";
  dataset_version?: string;
  source: HarnessSource;
  started_at: string;
  finished_at: string | null;
  state: "running" | "completed" | "error";
  model: string | null;
  answer: string | null;
  answer_truncated: boolean;
  steps: HarnessStep[];
  evidence: HarnessEvidence[];
  claim: {
    evidence_id: string; claimed_value: string; unit: string;
    store_id?: string; previous_year?: number; current_year?: number; year?: number | null;
  } | null;
  result: HarnessValidationResult | null;
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) throw new Error(`请求失败（HTTP ${response.status}）`);
  return response.json() as Promise<T>;
}

export function listHarnessRuns(conversationId: string | null) {
  const query = conversationId ? `?conversation_id=${encodeURIComponent(conversationId)}` : "";
  return request<HarnessRun[]>(`/api/harness/runs${query}`);
}

export function createHarnessRun(
  conversationId: string | null,
  source: HarnessRun["source"],
  claimedValue: string,
) {
  return submitHarnessRun({ conversation_id: conversationId, source, claimed_value: claimedValue });
}

// Shared object-based entry point; the existing UI keeps its positional wrapper.
export function submitHarnessRun(body: HarnessRunRequest) {
  return request<HarnessRun>("/api/harness/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function getHarnessRun(runId: string) {
  return request<HarnessRun>(`/api/harness/runs/${encodeURIComponent(runId)}`);
}
