import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { FleetView } from "../src/components/FleetView";
import type { Workload } from "../src/types";

const sample: Workload[] = [
  {
    id: "docker:mac-mini:nginx",
    host_id: "mac-mini",
    kind: "docker",
    name: "nginx",
    monitored: true,
    pinned: false,
    status: "running",
    severity: "green",
    severity_reason: null,
    last_seen: null,
    metadata: {},
  },
];

describe("FleetView fetch", () => {
  it("shows error when fetch fails", async () => {
    render(
      <FleetView
        client={{
          fetchWorkloads: vi.fn().mockRejectedValue(new Error("network down")),
          fetchLogs: vi.fn(),
        }}
      />,
    );
    expect(await screen.findByText("network down")).toBeInTheDocument();
  });

  it("shows empty message when no workloads", () => {
    render(
      <FleetView
        client={{
          fetchWorkloads: vi.fn().mockResolvedValue([]),
          fetchLogs: vi.fn(),
        }}
        initialWorkloads={[]}
      />,
    );
    expect(screen.getByText("No monitored workloads.")).toBeInTheDocument();
  });

  it("loads workloads from API on mount", async () => {
    const fetchWorkloads = vi.fn().mockResolvedValue(sample);
    render(<FleetView client={{ fetchWorkloads, fetchLogs: vi.fn() }} />);
    await waitFor(() => {
      expect(fetchWorkloads).toHaveBeenCalledWith(true);
    });
    expect(await screen.findByText("nginx")).toBeInTheDocument();
  });
});
