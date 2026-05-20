import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
    last_seen: "2026-01-01T00:00:00+00:00",
    metadata: {},
  },
  {
    id: "docker:vultr-1:api",
    host_id: "vultr-1",
    kind: "docker",
    name: "api",
    monitored: true,
    pinned: false,
    status: "running",
    severity: "red",
    severity_reason: "unhealthy",
    last_seen: "2026-01-01T00:00:00+00:00",
    metadata: {},
  },
];

function mockClient(overrides: Partial<FleetClient> = {}): FleetClient {
  return {
    fetchWorkloads: vi.fn().mockResolvedValue(sample),
    fetchLogs: vi.fn().mockResolvedValue("log output\n"),
    ...overrides,
  };
}

function renderFleet(client: FleetClient, workloads = sample) {
  return render(
    <FleetView client={client} initialWorkloads={workloads} />,
  );
}

describe("FleetView", () => {
  // AC-10.1
  it("renders workload name and status", () => {
    renderFleet(mockClient());
    expect(screen.getByText("nginx")).toBeInTheDocument();
    expect(screen.getAllByText("running").length).toBeGreaterThan(0);
  });

  // AC-10.2
  it("renders two host sections", () => {
    renderFleet(mockClient());
    expect(screen.getByRole("heading", { name: "mac-mini" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "vultr-1" })).toBeInTheDocument();
  });

  // AC-10.3
  it("marks red severity on row", () => {
    renderFleet(mockClient());
    const section = screen.getByRole("heading", { name: "vultr-1" }).closest("section")!;
    const tr = within(section).getByText("api").closest("tr");
    expect(tr).toHaveAttribute("data-severity", "red");
  });

  // AC-10.4 & AC-10.5
  it("opens logs modal with fetched text", async () => {
    const fetchLogs = vi.fn().mockResolvedValue("hello from container\n");
    const user = userEvent.setup();
    renderFleet(mockClient({ fetchLogs }));

    const section = screen.getByRole("heading", { name: "mac-mini" }).closest("section")!;
    await user.click(within(section).getByRole("button", { name: "Logs" }));

    await waitFor(() => {
      expect(fetchLogs).toHaveBeenCalledWith("docker:mac-mini:nginx");
    });
    expect(
      await screen.findByText("hello from container", { exact: false }),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Close" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("shows orange severity dot", () => {
    const orange: Workload = {
      ...sample[0],
      id: "docker:mac-mini:cache",
      name: "cache",
      severity: "orange",
    };
    renderFleet(mockClient(), [orange]);
    expect(screen.getByText("orange")).toBeInTheDocument();
  });

  it("shows logs fetch error for non-Error rejection", async () => {
    const fetchLogs = vi.fn().mockRejectedValue("boom");
    const user = userEvent.setup();
    renderFleet(mockClient({ fetchLogs }));

    const section = screen.getByRole("heading", { name: "mac-mini" }).closest("section")!;
    await user.click(within(section).getByRole("button", { name: "Logs" }));

    expect(await screen.findByText(/Error: fetch failed/)).toBeInTheDocument();
  });

  it("shows logs fetch error message from Error", async () => {
    const fetchLogs = vi.fn().mockRejectedValue(new Error("ssh timeout"));
    const user = userEvent.setup();
    renderFleet(mockClient({ fetchLogs }));

    const section = screen.getByRole("heading", { name: "mac-mini" }).closest("section")!;
    await user.click(within(section).getByRole("button", { name: "Logs" }));

    expect(await screen.findByText(/Error: ssh timeout/)).toBeInTheDocument();
  });
});
