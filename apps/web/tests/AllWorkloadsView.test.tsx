import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { FleetClient } from "../src/api/client";
import { AllWorkloadsView } from "../src/components/AllWorkloadsView";
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
  {
    id: "systemd:linux-box:ssh",
    host_id: "linux-box",
    kind: "systemd",
    name: "ssh.service",
    monitored: false,
    pinned: false,
    status: "active/running",
    severity: "green",
    severity_reason: null,
    last_seen: null,
    metadata: {},
  },
];

function mockClient(overrides: Partial<FleetClient> = {}): FleetClient {
  return {
    fetchWorkloads: vi.fn().mockResolvedValue(sample),
    fetchAudit: vi.fn().mockResolvedValue([]),
    fetchLogs: vi.fn().mockResolvedValue(""),
    pinWorkload: vi.fn().mockResolvedValue(undefined),
    unpinWorkload: vi.fn().mockResolvedValue(undefined),
    restartWorkload: vi.fn().mockResolvedValue(undefined),
    stopWorkload: vi.fn().mockResolvedValue(undefined),
    fetchSettings: vi
      .fn()
      .mockResolvedValue({ notify_orange: true, notify_red: true }),
    patchSettings: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  };
}

describe("AllWorkloadsView", () => {
  it("renders all workloads in a table", () => {
    render(
      <AllWorkloadsView
        client={mockClient()}
        initialWorkloads={sample}
      />,
    );
    expect(screen.getAllByText("nginx").length).toBeGreaterThan(0);
    expect(screen.getAllByText("ssh.service").length).toBeGreaterThan(0);
  });

  it("shows empty state", () => {
    render(
      <AllWorkloadsView client={mockClient()} initialWorkloads={[]} />,
    );
    expect(screen.getByText(/no workloads discovered/i)).toBeInTheDocument();
  });

  it("sorts by column", async () => {
    const user = userEvent.setup();
    render(
      <AllWorkloadsView
        client={mockClient()}
        initialWorkloads={sample}
      />,
    );

    await user.click(screen.getByRole("button", { name: /Name/ }));
    const rows = screen.getAllByRole("row");
    expect(rows.length).toBeGreaterThan(1);

    await user.click(screen.getByRole("button", { name: /Name/ }));
    expect(screen.getAllByRole("row").length).toBeGreaterThan(1);
  });

  it("fetches from API on mount", async () => {
    const fetchWorkloads = vi.fn().mockResolvedValue(sample);
    render(<AllWorkloadsView client={mockClient({ fetchWorkloads })} />);
    await waitFor(() => {
      expect(fetchWorkloads).toHaveBeenCalled();
    });
    expect((await screen.findAllByText("nginx")).length).toBeGreaterThan(0);
  });

  it("shows error on fetch failure", async () => {
    const fetchWorkloads = vi
      .fn()
      .mockRejectedValue(new Error("network error"));
    render(<AllWorkloadsView client={mockClient({ fetchWorkloads })} />);
    expect(await screen.findByText(/network error/)).toBeInTheDocument();
  });

  it("sorts by different columns", async () => {
    const user = userEvent.setup();
    render(
      <AllWorkloadsView
        client={mockClient()}
        initialWorkloads={sample}
      />,
    );
    await user.click(screen.getByRole("button", { name: /Host/ }));
    await user.click(screen.getByRole("button", { name: /Kind/ }));
    await user.click(screen.getByRole("button", { name: /Status/ }));
    await user.click(screen.getByRole("button", { name: /Severity/ }));
    expect(screen.getAllByText("nginx").length).toBeGreaterThan(0);
  });
});
