import type { HostGroup, Workload } from "../types";

export interface Settings {
  notify_orange: boolean;
  notify_red: boolean;
}

export interface FleetClient {
  fetchWorkloads(monitored?: boolean): Promise<Workload[]>;
  fetchAudit(): Promise<Workload[]>;
  fetchLogs(workloadId: string, tail?: number): Promise<string>;
  pinWorkload(workloadId: string): Promise<void>;
  unpinWorkload(workloadId: string): Promise<void>;
  restartWorkload(workloadId: string): Promise<void>;
  stopWorkload(workloadId: string): Promise<void>;
  fetchSettings(): Promise<Settings>;
  patchSettings(patch: Partial<Settings>): Promise<void>;
}

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function groupByHost(workloads: Workload[]): HostGroup[] {
  const map = new Map<string, Workload[]>();
  for (const workload of workloads) {
    const list = map.get(workload.host_id) ?? [];
    list.push(workload);
    map.set(workload.host_id, list);
  }
  return Array.from(map.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([hostId, hostWorkloads]) => ({
      hostId,
      workloads: hostWorkloads.sort((x, y) => x.name.localeCompare(y.name)),
    }));
}

export function createFleetClient(baseUrl = ""): FleetClient {
  async function request(path: string, init?: RequestInit): Promise<Response> {
    return fetch(`${baseUrl}${path}`, init);
  }

  async function ensureOk(response: Response): Promise<void> {
    if (!response.ok) {
      throw new ApiError(response.status, await response.text());
    }
  }

  return {
    async fetchWorkloads(monitored?: boolean) {
      const query = monitored === undefined ? "" : `?monitored=${monitored}`;
      const response = await request(`/api/workloads${query}`);
      await ensureOk(response);
      return (await response.json()) as Workload[];
    },

    async fetchAudit() {
      const response = await request("/api/audit");
      await ensureOk(response);
      return (await response.json()) as Workload[];
    },

    async fetchLogs(workloadId: string, tail = 200) {
      const encoded = encodeURIComponent(workloadId);
      const response = await request(
        `/api/workloads/${encoded}/logs?tail=${tail}`,
      );
      await ensureOk(response);
      return response.text();
    },

    async pinWorkload(workloadId: string) {
      const encoded = encodeURIComponent(workloadId);
      const response = await request(`/api/workloads/${encoded}/pin`, {
        method: "POST",
      });
      await ensureOk(response);
    },

    async unpinWorkload(workloadId: string) {
      const encoded = encodeURIComponent(workloadId);
      const response = await request(`/api/workloads/${encoded}/pin`, {
        method: "DELETE",
      });
      await ensureOk(response);
    },

    async restartWorkload(workloadId: string) {
      const encoded = encodeURIComponent(workloadId);
      const response = await request(`/api/workloads/${encoded}/restart`, {
        method: "POST",
      });
      await ensureOk(response);
    },

    async stopWorkload(workloadId: string) {
      const encoded = encodeURIComponent(workloadId);
      const response = await request(`/api/workloads/${encoded}/stop?confirm=1`, {
        method: "POST",
      });
      await ensureOk(response);
    },

    async fetchSettings() {
      const response = await request("/api/settings");
      await ensureOk(response);
      return (await response.json()) as Settings;
    },

    async patchSettings(patch: Partial<Settings>) {
      const response = await request("/api/settings", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patch),
      });
      await ensureOk(response);
    },
  };
}
