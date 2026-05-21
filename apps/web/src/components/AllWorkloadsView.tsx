import { useCallback, useEffect, useState } from "react";
import type { FleetClient } from "../api/client";
import type { Workload } from "../types";

interface AllWorkloadsViewProps {
  client: FleetClient;
  initialWorkloads?: Workload[];
}

type SortKey = "host_id" | "name" | "kind" | "status" | "severity";

export function AllWorkloadsView({
  client,
  initialWorkloads,
}: AllWorkloadsViewProps) {
  const [workloads, setWorkloads] = useState<Workload[]>(
    initialWorkloads ?? [],
  );
  const [error, setError] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>("host_id");
  const [sortAsc, setSortAsc] = useState(true);

  useEffect(() => {
    if (initialWorkloads !== undefined) {
      return;
    }
    let cancelled = false;
    client
      .fetchWorkloads()
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

  const handleSort = useCallback(
    (key: SortKey) => {
      if (key === sortKey) {
        setSortAsc(!sortAsc);
      } else {
        setSortKey(key);
        setSortAsc(true);
      }
    },
    [sortKey, sortAsc],
  );

  const sorted = [...workloads].sort((a, b) => {
    const cmp = String(a[sortKey]).localeCompare(String(b[sortKey]));
    return sortAsc ? cmp : -cmp;
  });

  return (
    <div>
      {error && (
        <p className="mb-4 rounded-lg border border-fault-red/40 bg-crimson-depth/40 p-3 text-sm text-fault-red">
          {error}
        </p>
      )}

      {workloads.length === 0 && !error && (
        <p className="text-sm text-mist">No workloads discovered yet.</p>
      )}

      {sorted.length > 0 && (
        <>
          <table className="hidden w-full border-collapse text-sm sm:table">
            <thead>
              <tr className="border-b border-border text-left text-xs text-fog">
                <SortHeader
                  label="Host"
                  sortKey="host_id"
                  current={sortKey}
                  asc={sortAsc}
                  onClick={handleSort}
                />
                <SortHeader
                  label="Name"
                  sortKey="name"
                  current={sortKey}
                  asc={sortAsc}
                  onClick={handleSort}
                />
                <SortHeader
                  label="Kind"
                  sortKey="kind"
                  current={sortKey}
                  asc={sortAsc}
                  onClick={handleSort}
                />
                <SortHeader
                  label="Status"
                  sortKey="status"
                  current={sortKey}
                  asc={sortAsc}
                  onClick={handleSort}
                />
                <SortHeader
                  label="Severity"
                  sortKey="severity"
                  current={sortKey}
                  asc={sortAsc}
                  onClick={handleSort}
                />
              </tr>
            </thead>
            <tbody>
              {sorted.map((w) => (
                <tr
                  key={w.id}
                  className="border-b border-border/60 bg-row transition-colors hover:bg-deep-slate"
                >
                  <td className="px-3 py-2 text-mist">{w.host_id}</td>
                  <td className="px-3 py-2 font-medium text-ghost-white">
                    {w.name}
                  </td>
                  <td className="px-3 py-2 text-mist">{w.kind}</td>
                  <td className="px-3 py-2 text-ice-blue">{w.status}</td>
                  <td className="px-3 py-2 text-ice-blue">{w.severity}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="space-y-2 sm:hidden">
            {sorted.map((w) => (
              <div
                key={w.id}
                className="rounded-lg border border-border bg-row p-3"
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium text-ghost-white">{w.name}</span>
                  <span className="text-xs text-mist">{w.severity}</span>
                </div>
                <div className="mt-1 text-xs text-fog">
                  {w.host_id} &middot; {w.kind} &middot; {w.status}
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function SortHeader({
  label,
  sortKey,
  current,
  asc,
  onClick,
}: {
  label: string;
  sortKey: SortKey;
  current: SortKey;
  asc: boolean;
  onClick: (key: SortKey) => void;
}) {
  const arrow = sortKey === current ? (asc ? " ↑" : " ↓") : "";
  return (
    <th className="px-3 py-2 font-medium">
      <button
        type="button"
        className="text-fog transition-colors hover:text-ice-blue"
        onClick={() => onClick(sortKey)}
      >
        {label}
        {arrow}
      </button>
    </th>
  );
}
