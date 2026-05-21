import { useCallback, useEffect, useState } from "react";
import type { FleetClient } from "../api/client";
import type { Workload } from "../types";

interface AuditViewProps {
  client: FleetClient;
  initialWorkloads?: Workload[];
}

export function AuditView({ client, initialWorkloads }: AuditViewProps) {
  const [workloads, setWorkloads] = useState<Workload[]>(
    initialWorkloads ?? [],
  );
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (initialWorkloads !== undefined) {
      return;
    }
    let cancelled = false;
    client
      .fetchAudit()
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

  const handlePin = useCallback(
    async (workload: Workload) => {
      try {
        await client.pinWorkload(workload.id);
        setWorkloads((prev) => prev.filter((w) => w.id !== workload.id));
      } catch (err) {
        setError(err instanceof Error ? err.message : "pin failed");
      }
    },
    [client],
  );

  return (
    <div>
      {error && (
        <p className="mb-4 rounded border border-red-900 bg-red-950/40 p-3 text-sm text-red-300">
          {error}
        </p>
      )}

      {workloads.length === 0 && !error && (
        <p className="text-sm text-gray-500">
          No discovered workloads pending review.
        </p>
      )}

      {workloads.length > 0 && (
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs text-gray-500">
              <th className="px-3 py-2 font-medium">Name</th>
              <th className="px-3 py-2 font-medium">Host</th>
              <th className="px-3 py-2 font-medium">Kind</th>
              <th className="px-3 py-2 font-medium">Status</th>
              <th className="px-3 py-2 font-medium" />
            </tr>
          </thead>
          <tbody>
            {workloads.map((workload) => (
              <tr
                key={workload.id}
                className="border-b border-border/60 bg-row hover:bg-[#2a2a32]"
              >
                <td className="px-3 py-2 font-medium">{workload.name}</td>
                <td className="px-3 py-2 text-gray-400">{workload.host_id}</td>
                <td className="px-3 py-2 text-gray-400">{workload.kind}</td>
                <td className="px-3 py-2 text-gray-300">{workload.status}</td>
                <td className="px-3 py-2 text-right">
                  <button
                    type="button"
                    className="rounded border border-emerald-700 bg-emerald-900/30 px-2 py-1 text-xs text-emerald-300 hover:bg-emerald-900/50"
                    onClick={() => handlePin(workload)}
                  >
                    Pin
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
