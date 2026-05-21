import { describe, expect, it, vi } from "vitest";
import { ApiError, createFleetClient, groupByHost } from "../src/api/client";
import type { Workload } from "../src/types";

const sample: Workload[] = [
  {
    id: "docker:h1:a",
    host_id: "h1",
    kind: "docker",
    name: "a",
    monitored: true,
    pinned: false,
    status: "running",
    severity: "green",
    severity_reason: null,
    last_seen: null,
    metadata: {},
  },
  {
    id: "docker:h2:b",
    host_id: "h2",
    kind: "docker",
    name: "b",
    monitored: true,
    pinned: false,
    status: "running",
    severity: "red",
    severity_reason: "unhealthy",
    last_seen: null,
    metadata: {},
  },
];

function stubFetch(response: Partial<Response>) {
  const mock = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => [],
    text: async () => "",
    ...response,
  });
  vi.stubGlobal("fetch", mock);
  return mock;
}

describe("groupByHost", () => {
  it("groups workloads by host_id", () => {
    const groups = groupByHost(sample);
    expect(groups).toHaveLength(2);
    expect(groups[0].hostId).toBe("h1");
    expect(groups[1].hostId).toBe("h2");
  });
});

describe("createFleetClient", () => {
  it("fetchWorkloads calls monitored query", async () => {
    const mock = stubFetch({ json: async () => sample });
    const client = createFleetClient("");
    const rows = await client.fetchWorkloads(true);
    expect(rows).toHaveLength(2);
    expect(mock).toHaveBeenCalledWith("/api/workloads?monitored=true", undefined);
    vi.unstubAllGlobals();
  });

  it("omits monitored query when argument is undefined", async () => {
    const mock = stubFetch({ json: async () => sample });
    const client = createFleetClient("");
    await client.fetchWorkloads(undefined);
    expect(mock).toHaveBeenCalledWith("/api/workloads", undefined);
    vi.unstubAllGlobals();
  });

  it("fetchLogs returns text", async () => {
    stubFetch({ text: async () => "line1\n" });
    const client = createFleetClient("");
    const text = await client.fetchLogs("docker:h1:a");
    expect(text).toBe("line1\n");
    vi.unstubAllGlobals();
  });

  it("throws ApiError on failure", async () => {
    stubFetch({ ok: false, status: 502, text: async () => "bad" });
    const client = createFleetClient("");
    await expect(client.fetchLogs("x")).rejects.toBeInstanceOf(ApiError);
    vi.unstubAllGlobals();
  });

  it("throws ApiError when workloads request fails", async () => {
    stubFetch({ ok: false, status: 500, text: async () => "nope" });
    const client = createFleetClient("");
    await expect(client.fetchWorkloads()).rejects.toBeInstanceOf(ApiError);
    vi.unstubAllGlobals();
  });

  it("fetchAudit returns audit workloads", async () => {
    const mock = stubFetch({ json: async () => sample });
    const client = createFleetClient("");
    const rows = await client.fetchAudit();
    expect(rows).toHaveLength(2);
    expect(mock).toHaveBeenCalledWith("/api/audit", undefined);
    vi.unstubAllGlobals();
  });

  it("fetchAudit throws ApiError on failure", async () => {
    stubFetch({ ok: false, status: 500, text: async () => "err" });
    const client = createFleetClient("");
    await expect(client.fetchAudit()).rejects.toBeInstanceOf(ApiError);
    vi.unstubAllGlobals();
  });

  it("pinWorkload calls POST", async () => {
    const mock = stubFetch({});
    const client = createFleetClient("");
    await client.pinWorkload("docker:h1:a");
    expect(mock).toHaveBeenCalledWith(
      "/api/workloads/docker%3Ah1%3Aa/pin",
      { method: "POST" },
    );
    vi.unstubAllGlobals();
  });

  it("unpinWorkload calls DELETE", async () => {
    const mock = stubFetch({});
    const client = createFleetClient("");
    await client.unpinWorkload("docker:h1:a");
    expect(mock).toHaveBeenCalledWith(
      "/api/workloads/docker%3Ah1%3Aa/pin",
      { method: "DELETE" },
    );
    vi.unstubAllGlobals();
  });

  it("restartWorkload calls POST", async () => {
    const mock = stubFetch({});
    const client = createFleetClient("");
    await client.restartWorkload("docker:h1:a");
    expect(mock).toHaveBeenCalledWith(
      "/api/workloads/docker%3Ah1%3Aa/restart",
      { method: "POST" },
    );
    vi.unstubAllGlobals();
  });

  it("stopWorkload calls POST with confirm", async () => {
    const mock = stubFetch({});
    const client = createFleetClient("");
    await client.stopWorkload("docker:h1:a");
    expect(mock).toHaveBeenCalledWith(
      "/api/workloads/docker%3Ah1%3Aa/stop?confirm=1",
      { method: "POST" },
    );
    vi.unstubAllGlobals();
  });

  it("pinWorkload throws ApiError on failure", async () => {
    stubFetch({ ok: false, status: 404, text: async () => "not found" });
    const client = createFleetClient("");
    await expect(client.pinWorkload("x")).rejects.toBeInstanceOf(ApiError);
    vi.unstubAllGlobals();
  });

  it("unpinWorkload throws ApiError on failure", async () => {
    stubFetch({ ok: false, status: 404, text: async () => "not found" });
    const client = createFleetClient("");
    await expect(client.unpinWorkload("x")).rejects.toBeInstanceOf(ApiError);
    vi.unstubAllGlobals();
  });

  it("restartWorkload throws ApiError on failure", async () => {
    stubFetch({ ok: false, status: 502, text: async () => "failed" });
    const client = createFleetClient("");
    await expect(client.restartWorkload("x")).rejects.toBeInstanceOf(ApiError);
    vi.unstubAllGlobals();
  });

  it("stopWorkload throws ApiError on failure", async () => {
    stubFetch({ ok: false, status: 502, text: async () => "failed" });
    const client = createFleetClient("");
    await expect(client.stopWorkload("x")).rejects.toBeInstanceOf(ApiError);
    vi.unstubAllGlobals();
  });

  it("fetchSettings returns settings", async () => {
    const data = { notify_orange: true, notify_red: false };
    const mock = stubFetch({ json: async () => data });
    const client = createFleetClient("");
    const settings = await client.fetchSettings();
    expect(settings).toEqual(data);
    expect(mock).toHaveBeenCalledWith("/api/settings", undefined);
    vi.unstubAllGlobals();
  });

  it("fetchSettings throws ApiError on failure", async () => {
    stubFetch({ ok: false, status: 500, text: async () => "err" });
    const client = createFleetClient("");
    await expect(client.fetchSettings()).rejects.toBeInstanceOf(ApiError);
    vi.unstubAllGlobals();
  });

  it("patchSettings calls PATCH", async () => {
    const mock = stubFetch({});
    const client = createFleetClient("");
    await client.patchSettings({ notify_orange: false });
    expect(mock).toHaveBeenCalledWith("/api/settings", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ notify_orange: false }),
    });
    vi.unstubAllGlobals();
  });

  it("patchSettings throws ApiError on failure", async () => {
    stubFetch({ ok: false, status: 400, text: async () => "bad" });
    const client = createFleetClient("");
    await expect(
      client.patchSettings({ notify_orange: false }),
    ).rejects.toBeInstanceOf(ApiError);
    vi.unstubAllGlobals();
  });
});
