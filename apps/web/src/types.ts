export type Severity = "green" | "orange" | "red";

export interface Workload {
  id: string;
  host_id: string;
  kind: string;
  name: string;
  monitored: boolean;
  pinned: boolean;
  status: string;
  severity: Severity;
  severity_reason: string | null;
  last_seen: string | null;
  metadata: Record<string, unknown>;
}

export interface HostGroup {
  hostId: string;
  workloads: Workload[];
}


