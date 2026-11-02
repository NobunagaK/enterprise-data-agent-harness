export interface HarnessRun {
  id: string;
  conversation_id: string | null;
  source: "test_injected" | "agent_generated";
  started_at: string;
  finished_at: string | null;
  state: "running" | "completed" | "error";
  model: string | null;
  answer: string | null;
  answer_truncated: boolean;
  steps: { id: string; kind: string; status: string; duration_ms: number; error: string | null }[];
  evidence: {
    id: string; run_id: string; step_id: string; sql: string;
    columns: string[]; rows: Record<string, unknown>[]; truncated: boolean;
    dataset_version: string; amount_unit: string;
  }[];
  claim: { evidence_id: string; claimed_value: string; unit: string } | null;
  result: {
    status: "passed" | "failed" | "unverifiable" | "tool_error";
    reason: string; rule_version: string; tolerance_pp: string;
    expected_value: string | null; expected_display: string | null;
    claimed_value: string | null; difference_pp: string | null;
  } | null;
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
  return request<HarnessRun>("/api/harness/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ conversation_id: conversationId, source, claimed_value: claimedValue }),
  });
}
