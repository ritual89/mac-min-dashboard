import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("../src/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../src/api/client")>();
  return {
    ...actual,
    createFleetClient: () => ({
      fetchWorkloads: vi.fn().mockResolvedValue([]),
      fetchLogs: vi.fn(),
    }),
  };
});

import { App } from "../src/App";

describe("App", () => {
  it("renders fleet view shell", async () => {
    render(<App />);
    expect(screen.getByRole("heading", { name: "Fleet" })).toBeInTheDocument();
    expect(await screen.findByText("No monitored workloads.")).toBeInTheDocument();
  });
});
