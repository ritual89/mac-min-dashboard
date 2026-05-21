import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { FleetClient } from "../src/api/client";
import { AuditView } from "../src/components/AuditView";
import type { Workload } from "../src/types";

const discovered: Workload[] = [
  {
    id: "launchd:mac-mini:com.custom.svc",
    host_id: "mac-mini",
    kind: "launchd",
    name: "com.custom.svc",
    monitored: false,
    pinned: false,
    status: "running",
    severity: "green",
    severity_reason: null,
    last_seen: "2026-01-01T00:00:00+00:00",
    metadata: {},
  },
];

function mockClient(overrides: Partial<FleetClient> = {}): FleetClient {
  return {
    fetchWorkloads: vi.fn().mockResolvedValue([]),
    fetchAudit: vi.fn().mockResolvedValue(discovered),
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

describe("AuditView", () => {
  it("renders discovered workloads", () => {
    render(
      <AuditView client={mockClient()} initialWorkloads={discovered} />,
    );
    expect(screen.getByText("com.custom.svc")).toBeInTheDocument();
    expect(screen.getByText("launchd")).toBeInTheDocument();
  });

  it("shows empty state when no workloads", () => {
    render(<AuditView client={mockClient()} initialWorkloads={[]} />);
    expect(screen.getByText(/no discovered workloads/i)).toBeInTheDocument();
  });

  it("pin button removes workload from list", async () => {
    const pinWorkload = vi.fn().mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(
      <AuditView
        client={mockClient({ pinWorkload })}
        initialWorkloads={discovered}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Pin" }));
    await waitFor(() => {
      expect(pinWorkload).toHaveBeenCalledWith("launchd:mac-mini:com.custom.svc");
    });
    expect(screen.queryByText("com.custom.svc")).not.toBeInTheDocument();
  });

  it("shows error on pin failure", async () => {
    const pinWorkload = vi.fn().mockRejectedValue(new Error("pin failed"));
    const user = userEvent.setup();
    render(
      <AuditView
        client={mockClient({ pinWorkload })}
        initialWorkloads={discovered}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Pin" }));
    expect(await screen.findByText(/pin failed/)).toBeInTheDocument();
  });

  it("shows error on pin non-Error rejection", async () => {
    const pinWorkload = vi.fn().mockRejectedValue("boom");
    const user = userEvent.setup();
    render(
      <AuditView
        client={mockClient({ pinWorkload })}
        initialWorkloads={discovered}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Pin" }));
    expect(await screen.findByText(/pin failed/)).toBeInTheDocument();
  });

  it("fetches audit data when no initialWorkloads", async () => {
    const fetchAudit = vi.fn().mockResolvedValue(discovered);
    render(<AuditView client={mockClient({ fetchAudit })} />);
    await waitFor(() => {
      expect(fetchAudit).toHaveBeenCalled();
    });
    expect(await screen.findByText("com.custom.svc")).toBeInTheDocument();
  });

  it("shows fetch error", async () => {
    const fetchAudit = vi.fn().mockRejectedValue(new Error("network error"));
    render(<AuditView client={mockClient({ fetchAudit })} />);
    expect(await screen.findByText(/network error/)).toBeInTheDocument();
  });
});
