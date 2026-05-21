import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { FleetClient } from "../src/api/client";
import { SettingsView } from "../src/components/SettingsView";

function mockClient(overrides: Partial<FleetClient> = {}): FleetClient {
  return {
    fetchWorkloads: vi.fn().mockResolvedValue([]),
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

describe("SettingsView", () => {
  it("renders toggle switches with initial settings", () => {
    render(
      <SettingsView
        client={mockClient()}
        initialSettings={{ notify_orange: true, notify_red: false }}
      />,
    );
    const switches = screen.getAllByRole("switch");
    expect(switches).toHaveLength(2);
    expect(switches[0]).toHaveAttribute("aria-checked", "true");
    expect(switches[1]).toHaveAttribute("aria-checked", "false");
  });

  it("toggles setting and calls patchSettings", async () => {
    const patchSettings = vi.fn().mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(
      <SettingsView
        client={mockClient({ patchSettings })}
        initialSettings={{ notify_orange: true, notify_red: true }}
      />,
    );

    await user.click(screen.getAllByRole("switch")[0]);

    await waitFor(() => {
      expect(patchSettings).toHaveBeenCalledWith({ notify_orange: false });
    });

    expect(screen.getAllByRole("switch")[0]).toHaveAttribute(
      "aria-checked",
      "false",
    );
  });

  it("shows error on patch failure", async () => {
    const patchSettings = vi.fn().mockRejectedValue(new Error("save failed"));
    const user = userEvent.setup();
    render(
      <SettingsView
        client={mockClient({ patchSettings })}
        initialSettings={{ notify_orange: true, notify_red: true }}
      />,
    );

    await user.click(screen.getAllByRole("switch")[0]);
    expect(await screen.findByText(/save failed/)).toBeInTheDocument();
  });

  it("shows error on patch non-Error rejection", async () => {
    const patchSettings = vi.fn().mockRejectedValue("boom");
    const user = userEvent.setup();
    render(
      <SettingsView
        client={mockClient({ patchSettings })}
        initialSettings={{ notify_orange: true, notify_red: true }}
      />,
    );

    await user.click(screen.getAllByRole("switch")[0]);
    expect(await screen.findByText(/save failed/)).toBeInTheDocument();
  });

  it("fetches settings on mount when no initialSettings", async () => {
    const fetchSettings = vi
      .fn()
      .mockResolvedValue({ notify_orange: false, notify_red: true });
    render(<SettingsView client={mockClient({ fetchSettings })} />);

    await waitFor(() => {
      expect(fetchSettings).toHaveBeenCalled();
    });

    const switches = await screen.findAllByRole("switch");
    expect(switches[0]).toHaveAttribute("aria-checked", "false");
    expect(switches[1]).toHaveAttribute("aria-checked", "true");
  });

  it("shows error on fetch failure", async () => {
    const fetchSettings = vi
      .fn()
      .mockRejectedValue(new Error("network error"));
    render(<SettingsView client={mockClient({ fetchSettings })} />);
    expect(await screen.findByText(/network error/)).toBeInTheDocument();
  });

  it("shows loading state before settings arrive", () => {
    render(<SettingsView client={mockClient()} />);
    expect(screen.getByText(/loading settings/i)).toBeInTheDocument();
  });

  it("toggle red setting works", async () => {
    const patchSettings = vi.fn().mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(
      <SettingsView
        client={mockClient({ patchSettings })}
        initialSettings={{ notify_orange: true, notify_red: true }}
      />,
    );

    await user.click(screen.getAllByRole("switch")[1]);

    await waitFor(() => {
      expect(patchSettings).toHaveBeenCalledWith({ notify_red: false });
    });
  });
});
