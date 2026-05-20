import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { LogsModal } from "../src/components/LogsModal";

describe("LogsModal", () => {
  it("shows loading and calls onClose", async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(
      <LogsModal
        title="nginx"
        body=""
        loading
        error={null}
        onClose={onClose}
      />,
    );
    expect(screen.getByText("Loading…")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Close" }));
    expect(onClose).toHaveBeenCalled();
  });

  it("shows error and empty body", () => {
    const { rerender } = render(
      <LogsModal
        title="nginx"
        body=""
        loading={false}
        error="failed"
        onClose={() => {}}
      />,
    );
    expect(screen.getByText(/Error: failed/)).toBeInTheDocument();

    rerender(
      <LogsModal
        title="nginx"
        body=""
        loading={false}
        error={null}
        onClose={() => {}}
      />,
    );
    expect(screen.getByText("(empty)")).toBeInTheDocument();
  });
});
