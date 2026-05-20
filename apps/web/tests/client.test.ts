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
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => sample,
    });
    vi.stubGlobal("fetch", fetchMock);

    const client = createFleetClient("");
    const rows = await client.fetchWorkloads(true);
    expect(rows).toHaveLength(2);
    expect(fetchMock).toHaveBeenCalledWith("/api/workloads?monitored=true");

    vi.unstubAllGlobals();
  });

  it("omits monitored query when argument is undefined", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => sample,
    });
    vi.stubGlobal("fetch", fetchMock);

    const client = createFleetClient("");
    await client.fetchWorkloads(undefined);
    expect(fetchMock).toHaveBeenCalledWith("/api/workloads");

    vi.unstubAllGlobals();
  });

  it("fetchLogs returns text", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      text: async () => "line1\n",
    });
    vi.stubGlobal("fetch", fetchMock);

    const client = createFleetClient("");
    const text = await client.fetchLogs("docker:h1:a");
    expect(text).toBe("line1\n");

    vi.unstubAllGlobals();
  });

  it("throws ApiError on failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 502, text: async () => "bad" }),
    );
    const client = createFleetClient("");
    await expect(client.fetchLogs("x")).rejects.toBeInstanceOf(ApiError);
    vi.unstubAllGlobals();
  });

  it("throws ApiError when workloads request fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 500, text: async () => "nope" }),
    );
    const client = createFleetClient("");
    await expect(client.fetchWorkloads()).rejects.toBeInstanceOf(ApiError);
    vi.unstubAllGlobals();
  });
});
