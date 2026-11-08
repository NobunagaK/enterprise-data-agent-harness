import { afterEach, describe, expect, it, vi } from "vitest";
import { createHarnessRun, getHarnessRun, submitHarnessRun } from "../harness";

const fetchMock = vi.fn();
afterEach(() => { vi.unstubAllGlobals(); fetchMock.mockReset(); });

function respond() {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockResolvedValue({ ok: true, json: async () => ({ id: "run-1" }) });
}

describe("shared Harness client", () => {
  it("preserves the original page request", async () => {
    respond();
    await createHarnessRun(null, "test_injected", "10.01");
    expect(fetchMock.mock.calls[0][0]).toBe("/api/harness/runs");
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      conversation_id: null, source: "test_injected", claimed_value: "10.01",
    });
  });
  it("passes case identity and supported selectors without converting decimals", async () => {
    respond();
    const body = { case_id: "boundary", rule_id: "growth_rate", claimed_value: "10.010001" } as const;
    expect(await submitHarnessRun(body)).toEqual({ id: "run-1" });
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual(body);
  });
  it("encodes a report identity as one path segment", async () => {
    respond();
    await getHarnessRun("a/b?x=1");
    expect(fetchMock.mock.calls[0][0]).toBe("/api/harness/runs/a%2Fb%3Fx%3D1");
  });
  it("does not treat a rejected capability as a successful report", async () => {
    vi.stubGlobal("fetch", fetchMock);
    fetchMock.mockResolvedValue({ ok: false, status: 422 });
    await expect(submitHarnessRun({})).rejects.toThrow("HTTP 422");
  });
});
