import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { FleetClient } from "../src/api/client";
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

function mockClient(overrides: Partial<FleetClient> = {}): FleetClient {
  return {
    fetchWorkloads: vi.fn().mockResolvedValue([]),
    fetchAudit: vi.fn().mockResolvedValue([]),
    fetchLogs: vi.fn().mockResolvedValue(""),
    pinWorkload: vi.fn().mockResolvedValue(undefined),
    unpinWorkload: vi.fn().mockResolvedValue(undefined),
    restartWorkload: vi.fn().mockResolvedValue(undefined),
    stopWorkload: vi.fn().mockResolvedValue(undefined),
    fetchSettings: vi.fn().mockResolvedValue({ notify_orange: true, notify_red: true }),
    patchSettings: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  };
}

describe("FleetView fetch", () => {
  it("shows error when fetch fails", async () => {
    render(
      <FleetView
        client={mockClient({
          fetchWorkloads: vi.fn().mockRejectedValue(new Error("network down")),
        })}
      />,
    );
    expect(await screen.findByText("network down")).toBeInTheDocument();
  });

  it("shows empty message when no workloads", () => {
    render(
      <FleetView client={mockClient()} initialWorkloads={[]} />,
    );
    expect(screen.getByText("No monitored workloads.")).toBeInTheDocument();
  });

  it("loads workloads from API on mount", async () => {
    const fetchWorkloads = vi.fn().mockResolvedValue(sample);
    render(<FleetView client={mockClient({ fetchWorkloads })} />);
    await waitFor(() => {
      expect(fetchWorkloads).toHaveBeenCalledWith(true);
    });
    expect(await screen.findByText("nginx")).toBeInTheDocument();
  });
});
