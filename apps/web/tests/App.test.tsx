import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { App } from "../src/App";

function stubFetchOk() {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [],
      text: async () => "",
    }),
  );
}

describe("App", () => {
  it("renders Fleet heading and tabs", () => {
    stubFetchOk();
    render(<App />);
    expect(screen.getByRole("heading", { name: "Fleet" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Fleet" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Audit" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Settings" })).toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it("switches to audit view", async () => {
    stubFetchOk();
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("tab", { name: "Audit" }));
    await waitFor(() => {
      expect(
        screen.getByText(/no discovered workloads/i),
      ).toBeInTheDocument();
    });
    vi.unstubAllGlobals();
  });

  it("switches to all workloads view", async () => {
    stubFetchOk();
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("tab", { name: "All" }));
    await waitFor(() => {
      expect(
        screen.getByText(/no workloads discovered/i),
      ).toBeInTheDocument();
    });
    vi.unstubAllGlobals();
  });

  it("switches to settings view", async () => {
    stubFetchOk();
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("tab", { name: "Settings" }));
    expect(
      screen.getByText(/telegram notifications/i),
    ).toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it("switches back to fleet from settings", async () => {
    stubFetchOk();
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("tab", { name: "Settings" }));
    await user.click(screen.getByRole("tab", { name: "Fleet" }));
    expect(
      screen.queryByText(/settings coming soon/i),
    ).not.toBeInTheDocument();
    vi.unstubAllGlobals();
  });
});
