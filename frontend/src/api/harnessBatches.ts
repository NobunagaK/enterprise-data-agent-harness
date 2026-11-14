import type { HarnessSource, ValidationStatus } from "./harness";

export type BatchCaseState = "completed" | "timeout" | "error";
export type BatchState = "running" | "completed" | "partial" | "error";

export interface BatchCaseOutcome {
  case_id: string;
  state: BatchCaseState;
  run_id: string | null;
  result_status: ValidationStatus | null;
  reason: string | null;
  error_type?: string | null;
  expected_status: ValidationStatus | null;
  matches_expected: boolean | null;
  duration_ms: number;
}

export interface BatchCounts {
  attempted: number;
  completed: number;
  passed: number;
  failed: number;
  unverifiable: number;
  tool_error: number;
  timeout: number;
  error: number;
}

export interface HarnessBatch {
  schema_version: 1;
  id: string;
  case_set_id: string;
  case_set_version: string;
  conversation_id: string | null;
  state: BatchState;
  started_at: string;
  finished_at: string | null;
  outcomes: BatchCaseOutcome[];
  counts: BatchCounts;
}

export interface HarnessBatchRequest {
  case_set_id?: string;
  conversation_id?: string | null;
  case_timeout_s?: number | null;
}

export interface CaseSetSummary {
  case_set_id: string;
  version: string;
  dataset_version: string;
  case_count: number;
  rule_ids: string[];
  sources: HarnessSource[];
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) throw new Error(`请求失败（HTTP ${response.status}）`);
  return response.json() as Promise<T>;
}

export function createHarnessBatch(body: HarnessBatchRequest = {}) {
  return request<HarnessBatch>("/api/harness/batches", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function listHarnessCaseSets() {
  return request<CaseSetSummary[]>("/api/harness/batches/case-sets");
}

export function getHarnessBatch(batchId: string) {
  return request<HarnessBatch>(`/api/harness/batches/${encodeURIComponent(batchId)}`);
}

export function listHarnessBatches(conversationId: string | null) {
  const query = conversationId
    ? `?conversation_id=${encodeURIComponent(conversationId)}`
    : "";
  return request<HarnessBatch[]>(`/api/harness/batches${query}`);
}
