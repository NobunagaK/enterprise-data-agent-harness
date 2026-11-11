import { afterEach, describe, expect, it, vi } from "vitest";
import { createHarnessBatch, getHarnessBatch, listHarnessBatches } from "../harnessBatches";

const fetchMock = vi.fn();
afterEach(() => {
  vi.unstubAllGlobals();
  fetchMock.mockReset();
});

function respond() {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockResolvedValue({ ok: true, json: async () => ({ id: "batch-1" }) });
}

describe("batch client", () => {
  it("posts the default case set without inventing extra fields", async () => {
    respond();
    expect(await createHarnessBatch()).toEqual({ id: "batch-1" });
    expect(fetchMock.mock.calls[0][0]).toBe("/api/harness/batches");
    expect(fetchMock.mock.calls[0][1].method).toBe("POST");
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({});
  });

  it("passes a conversation and timeout through unchanged", async () => {
    respond();
    await createHarnessBatch({ conversation_id: "c1", case_timeout_s: 30 });
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      conversation_id: "c1",
      case_timeout_s: 30,
    });
  });

  it("encodes a batch identity as one path segment", async () => {
    respond();
    await getHarnessBatch("a/b?x=1");
    expect(fetchMock.mock.calls[0][0]).toBe("/api/harness/batches/a%2Fb%3Fx%3D1");
  });

  it("lists the selected conversation only", async () => {
    respond();
    await listHarnessBatches("c 1");
    expect(fetchMock.mock.calls[0][0]).toBe("/api/harness/batches?conversation_id=c%201");
    await listHarnessBatches(null);
    expect(fetchMock.mock.calls[1][0]).toBe("/api/harness/batches");
  });

  it("does not treat a rejected request as a saved batch", async () => {
    vi.stubGlobal("fetch", fetchMock);
    fetchMock.mockResolvedValue({ ok: false, status: 422 });
    await expect(createHarnessBatch()).rejects.toThrow("HTTP 422");
  });
});
