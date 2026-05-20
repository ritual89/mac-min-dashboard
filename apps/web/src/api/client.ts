import type { HostGroup, Workload } from "../types";

export interface FleetClient {
  fetchWorkloads(monitored?: boolean): Promise<Workload[]>;
  fetchLogs(workloadId: string, tail?: number): Promise<string>;
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
  async function request(path: string): Promise<Response> {
    return fetch(`${baseUrl}${path}`);
  }

  return {
    async fetchWorkloads(monitored?: boolean) {
      const query = monitored === undefined ? "" : `?monitored=${monitored}`;
      const response = await request(`/api/workloads${query}`);
      if (!response.ok) {
        throw new ApiError(response.status, await response.text());
      }
      return (await response.json()) as Workload[];
    },

    async fetchLogs(workloadId: string, tail = 200) {
      const encoded = encodeURIComponent(workloadId);
      const response = await request(
        `/api/workloads/${encoded}/logs?tail=${tail}`,
      );
      if (!response.ok) {
        throw new ApiError(response.status, await response.text());
      }
      return response.text();
    },
  };
}
