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
    fetchAudit: vi.fn().mockResolvedValue([]),
    fetchLogs: vi.fn().mockResolvedValue("log output\n"),
    pinWorkload: vi.fn().mockResolvedValue(undefined),
    unpinWorkload: vi.fn().mockResolvedValue(undefined),
    restartWorkload: vi.fn().mockResolvedValue(undefined),
    stopWorkload: vi.fn().mockResolvedValue(undefined),
    fetchSettings: vi.fn().mockResolvedValue({ notify_orange: true, notify_red: true }),
    patchSettings: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  };
}

function renderFleet(client: FleetClient, workloads = sample) {
  return render(
    <FleetView client={client} initialWorkloads={workloads} />,
  );
}

describe("FleetView", () => {
  it("renders workload name and status", () => {
    renderFleet(mockClient());
    expect(screen.getByText("nginx")).toBeInTheDocument();
    expect(screen.getAllByText("running").length).toBeGreaterThan(0);
  });

  it("renders two host sections", () => {
    renderFleet(mockClient());
    expect(screen.getByRole("heading", { name: "mac-mini" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "vultr-1" })).toBeInTheDocument();
  });

  it("marks red severity on row", () => {
    renderFleet(mockClient());
    const section = screen.getByRole("heading", { name: "vultr-1" }).closest("section")!;
    const tr = within(section).getByText("api").closest("tr");
    expect(tr).toHaveAttribute("data-severity", "red");
  });

  it("expands row on click and shows fetched logs", async () => {
    const fetchLogs = vi.fn().mockResolvedValue("hello from container\n");
    const user = userEvent.setup();
    renderFleet(mockClient({ fetchLogs }));

    await user.click(screen.getByText("nginx"));

    await waitFor(() => {
      expect(fetchLogs).toHaveBeenCalledWith("docker:mac-mini:nginx");
    });
    expect(
      await screen.findByText("hello from container", { exact: false }),
    ).toBeInTheDocument();
  });

  it("collapses expanded row on second click", async () => {
    const fetchLogs = vi.fn().mockResolvedValue("logs here");
    const user = userEvent.setup();
    renderFleet(mockClient({ fetchLogs }));

    await user.click(screen.getByText("nginx"));
    await screen.findByText("logs here");

    await user.click(screen.getByText("nginx"));
    expect(screen.queryByText("logs here")).not.toBeInTheDocument();
  });

  it("shows severity_reason when present", async () => {
    const user = userEvent.setup();
    renderFleet(mockClient());

    await user.click(screen.getByText("api"));
    expect(await screen.findByText("unhealthy")).toBeInTheDocument();
  });

  it("shows last_seen in expanded row", async () => {
    const user = userEvent.setup();
    renderFleet(mockClient());

    await user.click(screen.getByText("nginx"));
    expect(await screen.findByText("2026-01-01T00:00:00+00:00")).toBeInTheDocument();
  });

  it("shows metadata when present", async () => {
    const withMeta: Workload[] = [
      {
        ...sample[0],
        metadata: { image: "nginx:latest" },
      },
    ];
    const user = userEvent.setup();
    renderFleet(mockClient(), withMeta);

    await user.click(screen.getByText("nginx"));
    expect(await screen.findByText(/nginx:latest/)).toBeInTheDocument();
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

    await user.click(screen.getByText("nginx"));

    expect(await screen.findByText(/Error: fetch failed/)).toBeInTheDocument();
  });

  it("shows logs fetch error message from Error", async () => {
    const fetchLogs = vi.fn().mockRejectedValue(new Error("ssh timeout"));
    const user = userEvent.setup();
    renderFleet(mockClient({ fetchLogs }));

    await user.click(screen.getByText("nginx"));

    expect(await screen.findByText(/Error: ssh timeout/)).toBeInTheDocument();
  });

  it("shows empty logs placeholder", async () => {
    const fetchLogs = vi.fn().mockResolvedValue("");
    const user = userEvent.setup();
    renderFleet(mockClient({ fetchLogs }));

    await user.click(screen.getByText("nginx"));
    expect(await screen.findByText("(empty)")).toBeInTheDocument();
  });

  it("restart button calls restartWorkload", async () => {
    const restartWorkload = vi.fn().mockResolvedValue(undefined);
    const user = userEvent.setup();
    renderFleet(mockClient({ restartWorkload }));

    await user.click(screen.getByText("nginx"));
    await screen.findByRole("button", { name: "Restart" });
    await user.click(screen.getByRole("button", { name: "Restart" }));

    await waitFor(() => {
      expect(restartWorkload).toHaveBeenCalledWith("docker:mac-mini:nginx");
    });
  });

  it("stop requires confirm click", async () => {
    const stopWorkload = vi.fn().mockResolvedValue(undefined);
    const user = userEvent.setup();
    renderFleet(mockClient({ stopWorkload }));

    await user.click(screen.getByText("nginx"));
    await screen.findByRole("button", { name: "Stop" });
    await user.click(screen.getByRole("button", { name: "Stop" }));
    expect(stopWorkload).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Confirm Stop" }));
    await waitFor(() => {
      expect(stopWorkload).toHaveBeenCalledWith("docker:mac-mini:nginx");
    });
  });

  it("shows action error on restart failure", async () => {
    const restartWorkload = vi.fn().mockRejectedValue(new Error("ssh down"));
    const user = userEvent.setup();
    renderFleet(mockClient({ restartWorkload }));

    await user.click(screen.getByText("nginx"));
    await screen.findByRole("button", { name: "Restart" });
    await user.click(screen.getByRole("button", { name: "Restart" }));

    expect(await screen.findByText(/ssh down/)).toBeInTheDocument();
  });

  it("shows action error on stop Error rejection", async () => {
    const stopWorkload = vi.fn().mockRejectedValue(new Error("access denied"));
    const user = userEvent.setup();
    renderFleet(mockClient({ stopWorkload }));

    await user.click(screen.getByText("nginx"));
    await screen.findByRole("button", { name: "Stop" });
    await user.click(screen.getByRole("button", { name: "Stop" }));
    await user.click(screen.getByRole("button", { name: "Confirm Stop" }));

    expect(await screen.findByText(/access denied/)).toBeInTheDocument();
  });

  it("shows action error on stop non-Error rejection", async () => {
    const stopWorkload = vi.fn().mockRejectedValue("boom");
    const user = userEvent.setup();
    renderFleet(mockClient({ stopWorkload }));

    await user.click(screen.getByText("nginx"));
    await screen.findByRole("button", { name: "Stop" });
    await user.click(screen.getByRole("button", { name: "Stop" }));
    await user.click(screen.getByRole("button", { name: "Confirm Stop" }));

    expect(await screen.findByText(/stop failed/)).toBeInTheDocument();
  });

  it("shows action error on restart non-Error rejection", async () => {
    const restartWorkload = vi.fn().mockRejectedValue("kaboom");
    const user = userEvent.setup();
    renderFleet(mockClient({ restartWorkload }));

    await user.click(screen.getByText("nginx"));
    await screen.findByRole("button", { name: "Restart" });
    await user.click(screen.getByRole("button", { name: "Restart" }));

    expect(await screen.findByText(/restart failed/)).toBeInTheDocument();
  });
});
