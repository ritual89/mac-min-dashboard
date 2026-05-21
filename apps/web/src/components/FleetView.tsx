import { useCallback, useEffect, useState } from "react";
import type { FleetClient } from "../api/client";
import { groupByHost } from "../api/client";
import type { Workload } from "../types";

interface FleetViewProps {
  client: FleetClient;
  initialWorkloads?: Workload[];
}

export function FleetView({ client, initialWorkloads }: FleetViewProps) {
  const [workloads, setWorkloads] = useState<Workload[]>(initialWorkloads ?? []);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [logsBody, setLogsBody] = useState("");
  const [logsLoading, setLogsLoading] = useState(false);
  const [logsError, setLogsError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [confirmStop, setConfirmStop] = useState<string | null>(null);

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

  const toggleExpand = useCallback(
    async (workload: Workload) => {
      if (expandedId === workload.id) {
        setExpandedId(null);
        return;
      }
      setExpandedId(workload.id);
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
    [client, expandedId],
  );

  const handleRestart = useCallback(
    async (workload: Workload) => {
      setActionError(null);
      try {
        await client.restartWorkload(workload.id);
      } catch (err) {
        setActionError(
          err instanceof Error ? err.message : "restart failed",
        );
      }
    },
    [client],
  );

  const handleStop = useCallback(
    async (workload: Workload) => {
      setActionError(null);
      try {
        await client.stopWorkload(workload.id);
      } catch (err) {
        setActionError(err instanceof Error ? err.message : "stop failed");
      } finally {
        setConfirmStop(null);
      }
    },
    [client],
  );

  const groups = groupByHost(workloads);

  return (
    <div>
      {error && (
        <p className="mb-4 rounded-lg border border-fault-red/40 bg-crimson-depth/40 p-3 text-sm text-fault-red">
          {error}
        </p>
      )}
      {actionError && (
        <p className="mb-4 rounded-lg border border-warning-amber/40 bg-warning-amber/10 p-3 text-sm text-warning-amber">
          {actionError}
        </p>
      )}

      {groups.length === 0 && !error && (
        <p className="text-sm text-mist">No monitored workloads.</p>
      )}

      {groups.map((group) => (
        <section key={group.hostId} className="mb-6">
          <h2 className="mb-2 text-xs font-medium uppercase tracking-wider text-fog">
            {group.hostId}
          </h2>
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs text-fog">
                <th className="px-3 py-2 font-medium">Name</th>
                <th className="px-3 py-2 font-medium">Kind</th>
                <th className="px-3 py-2 font-medium">Status</th>
                <th className="px-3 py-2 font-medium">Severity</th>
                <th className="w-8 px-3 py-2 font-medium" />
              </tr>
            </thead>
            <tbody>
              {group.workloads.map((workload) => {
                const isExpanded = expandedId === workload.id;
                return (
                  <ExpandableRow
                    key={workload.id}
                    workload={workload}
                    isExpanded={isExpanded}
                    logsBody={logsBody}
                    logsLoading={logsLoading}
                    logsError={logsError}
                    confirmStop={confirmStop}
                    onToggle={() => toggleExpand(workload)}
                    onRestart={() => handleRestart(workload)}
                    onStop={() => handleStop(workload)}
                    onConfirmStop={() => setConfirmStop(workload.id)}
                  />
                );
              })}
            </tbody>
          </table>
        </section>
      ))}
    </div>
  );
}

function ExpandableRow({
  workload,
  isExpanded,
  logsBody,
  logsLoading,
  logsError,
  confirmStop,
  onToggle,
  onRestart,
  onStop,
  onConfirmStop,
}: {
  workload: Workload;
  isExpanded: boolean;
  logsBody: string;
  logsLoading: boolean;
  logsError: string | null;
  confirmStop: string | null;
  onToggle: () => void;
  onRestart: () => void;
  onStop: () => void;
  onConfirmStop: () => void;
}) {
  return (
    <>
      <tr
        data-severity={workload.severity}
        className="cursor-pointer border-b border-border/60 bg-row transition-colors hover:bg-deep-slate"
        onClick={onToggle}
      >
        <td className="px-3 py-2 font-medium text-ghost-white">
          {workload.name}
        </td>
        <td className="px-3 py-2 text-mist">{workload.kind}</td>
        <td className="px-3 py-2 text-ice-blue">{workload.status}</td>
        <td className="px-3 py-2">
          <SeverityDot severity={workload.severity} />
        </td>
        <td className="px-3 py-2 text-right">
          <span
            className={`inline-block text-mist transition-transform ${isExpanded ? "rotate-90" : ""}`}
            aria-hidden="true"
          >
            ▶
          </span>
        </td>
      </tr>
      {isExpanded && (
        <tr className="border-b border-border/60 bg-abyssal">
          <td colSpan={5} className="px-3 py-4">
            <div className="space-y-3">
              <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs">
                {workload.severity_reason && (
                  <span>
                    <span className="text-fog">Reason:</span>{" "}
                    <span className="text-ice-blue">
                      {workload.severity_reason}
                    </span>
                  </span>
                )}
                {workload.last_seen && (
                  <span>
                    <span className="text-fog">Last seen:</span>{" "}
                    <span className="text-ice-blue">{workload.last_seen}</span>
                  </span>
                )}
                {Object.keys(workload.metadata).length > 0 && (
                  <span>
                    <span className="text-fog">Metadata:</span>{" "}
                    <span className="text-ice-blue">
                      {JSON.stringify(workload.metadata)}
                    </span>
                  </span>
                )}
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  className="rounded-full border border-border bg-steel-navy/20 px-3 py-1 text-xs text-ice-blue transition-colors hover:bg-steel-navy/50"
                  onClick={(e) => {
                    e.stopPropagation();
                    onRestart();
                  }}
                >
                  Restart
                </button>
                {confirmStop === workload.id ? (
                  <button
                    type="button"
                    className="rounded-full border border-fault-red/50 bg-fault-red/20 px-3 py-1 text-xs text-fault-red transition-colors hover:bg-fault-red/30"
                    onClick={(e) => {
                      e.stopPropagation();
                      onStop();
                    }}
                  >
                    Confirm Stop
                  </button>
                ) : (
                  <button
                    type="button"
                    className="rounded-full border border-border bg-steel-navy/20 px-3 py-1 text-xs text-mist transition-colors hover:bg-steel-navy/50"
                    onClick={(e) => {
                      e.stopPropagation();
                      onConfirmStop();
                    }}
                  >
                    Stop
                  </button>
                )}
              </div>

              <div>
                <h3 className="mb-1 text-xs font-medium text-fog">Logs</h3>
                <pre
                  className="max-h-[300px] overflow-y-auto rounded-lg bg-cosmic-void/60 p-3 text-xs leading-relaxed text-ice-blue"
                  style={{ whiteSpace: "pre-wrap", wordBreak: "break-all" }}
                >
                  {logsLoading && "Loading…"}
                  {!logsLoading && logsError && `Error: ${logsError}`}
                  {!logsLoading && !logsError && (logsBody || "(empty)")}
                </pre>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

function SeverityDot({ severity }: { severity: Workload["severity"] }) {
  const color =
    severity === "red"
      ? "bg-fault-red"
      : severity === "orange"
        ? "bg-warning-amber"
        : "bg-specimen-green";
  return (
    <span className="inline-flex items-center gap-2">
      <span className={`inline-block h-2.5 w-2.5 rounded-full ${color}`} />
      <span className="text-xs text-mist">{severity}</span>
    </span>
  );
}
