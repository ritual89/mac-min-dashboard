import { useCallback, useEffect, useState } from "react";
import type { FleetClient } from "../api/client";
import { groupByHost } from "../api/client";
import type { Workload } from "../types";
import { LogsModal } from "./LogsModal";

interface FleetViewProps {
  client: FleetClient;
  initialWorkloads?: Workload[];
}

export function FleetView({ client, initialWorkloads }: FleetViewProps) {
  const [workloads, setWorkloads] = useState<Workload[]>(initialWorkloads ?? []);
  const [error, setError] = useState<string | null>(null);
  const [logsOpen, setLogsOpen] = useState<string | null>(null);
  const [logsBody, setLogsBody] = useState("");
  const [logsLoading, setLogsLoading] = useState(false);
  const [logsError, setLogsError] = useState<string | null>(null);

  useEffect(() => {
    if (initialWorkloads !== undefined) {
      return;
    }
    let cancelled = false;
    client
      .fetchWorkloads(true)
      .then((rows) => {
        if (!cancelled) {
          setWorkloads(rows);
          setError(null);
        }
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setError(err.message);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [client, initialWorkloads]);

  const openLogs = useCallback(
    async (workload: Workload) => {
      setLogsOpen(workload.id);
      setLogsBody("");
      setLogsError(null);
      setLogsLoading(true);
      try {
        const text = await client.fetchLogs(workload.id);
        setLogsBody(text);
      } catch (err) {
        setLogsError(err instanceof Error ? err.message : "fetch failed");
      } finally {
        setLogsLoading(false);
      }
    },
    [client],
  );

  const groups = groupByHost(workloads);
  const active = workloads.find((w) => w.id === logsOpen);

  return (
    <div className="min-h-screen bg-black p-4">
      <header className="mb-4 flex items-center justify-between">
        <h1 className="text-lg font-semibold tracking-tight">Fleet</h1>
        <span className="text-xs text-gray-500">Monitored workloads</span>
      </header>

      {error && (
        <p className="mb-4 rounded border border-red-900 bg-red-950/40 p-3 text-sm text-red-300">
          {error}
        </p>
      )}

      {groups.length === 0 && !error && (
        <p className="text-sm text-gray-500">No monitored workloads.</p>
      )}

      {groups.map((group) => (
        <section key={group.hostId} className="mb-6">
          <h2 className="mb-2 text-xs font-medium uppercase tracking-wider text-gray-500">
            {group.hostId}
          </h2>
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs text-gray-500">
                <th className="px-3 py-2 font-medium">Name</th>
                <th className="px-3 py-2 font-medium">Kind</th>
                <th className="px-3 py-2 font-medium">Status</th>
                <th className="px-3 py-2 font-medium">Severity</th>
                <th className="px-3 py-2 font-medium" />
              </tr>
            </thead>
            <tbody>
              {group.workloads.map((workload) => (
                <tr
                  key={workload.id}
                  data-severity={workload.severity}
                  className="border-b border-border/60 bg-row hover:bg-[#2a2a32]"
                >
                  <td className="px-3 py-2 font-medium">{workload.name}</td>
                  <td className="px-3 py-2 text-gray-400">{workload.kind}</td>
                  <td className="px-3 py-2 text-gray-300">{workload.status}</td>
                  <td className="px-3 py-2">
                    <SeverityDot severity={workload.severity} />
                  </td>
                  <td className="px-3 py-2 text-right">
                    <button
                      type="button"
                      className="rounded border border-border px-2 py-1 text-xs hover:bg-panel"
                      onClick={() => openLogs(workload)}
                    >
                      Logs
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ))}

      {logsOpen && active && (
        <LogsModal
          title={active.name}
          body={logsBody}
          loading={logsLoading}
          error={logsError}
          onClose={() => setLogsOpen(null)}
        />
      )}
    </div>
  );
}

function SeverityDot({ severity }: { severity: Workload["severity"] }) {
  const color =
    severity === "red"
      ? "bg-red-500"
      : severity === "orange"
        ? "bg-orange-400"
        : "bg-emerald-500";
  return (
    <span className="inline-flex items-center gap-2">
      <span className={`inline-block h-2.5 w-2.5 rounded-full ${color}`} />
      <span className="text-xs text-gray-400">{severity}</span>
    </span>
  );
}
