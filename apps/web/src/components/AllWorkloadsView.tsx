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
        <p className="mb-4 rounded border border-red-900 bg-red-950/40 p-3 text-sm text-red-300">
          {error}
        </p>
      )}

      {workloads.length === 0 && !error && (
        <p className="text-sm text-gray-500">No workloads discovered yet.</p>
      )}

      {sorted.length > 0 && (
        <>
          <table className="hidden w-full border-collapse text-sm sm:table">
            <thead>
              <tr className="border-b border-border text-left text-xs text-gray-500">
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
                  className="border-b border-border/60 bg-row hover:bg-[#2a2a32]"
                >
                  <td className="px-3 py-2 text-gray-400">{w.host_id}</td>
                  <td className="px-3 py-2 font-medium">{w.name}</td>
                  <td className="px-3 py-2 text-gray-400">{w.kind}</td>
                  <td className="px-3 py-2 text-gray-300">{w.status}</td>
                  <td className="px-3 py-2 text-gray-300">{w.severity}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="space-y-2 sm:hidden">
            {sorted.map((w) => (
              <div
                key={w.id}
                className="rounded border border-border bg-row p-3"
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium">{w.name}</span>
                  <span className="text-xs text-gray-400">{w.severity}</span>
                </div>
                <div className="mt-1 text-xs text-gray-400">
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
        className="hover:text-gray-300"
        onClick={() => onClick(sortKey)}
      >
        {label}
        {arrow}
      </button>
    </th>
  );
}
