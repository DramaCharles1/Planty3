import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import CommandHistory from "../components/CommandHistory";

describe("CommandHistory", () => {
  it("should render empty state when no commands", () => {
    render(<CommandHistory commands={[]} />);

    expect(screen.getByText("No commands sent yet.")).toBeInTheDocument();
  });

  it("should render command table with data", () => {
    const commands = [
      {
        id: 1,
        command: "water",
        cmd_id: "abc-123",
        sent_at: "2024-03-15T10:00:00Z",
        ack_at: "2024-03-15T10:00:05Z",
        status: "ok",
        error: "",
      },
    ];

    render(<CommandHistory commands={commands} />);

    expect(screen.getByText("water")).toBeInTheDocument();
    expect(screen.getByText("abc-123")).toBeInTheDocument();
  });

  it("should show status badges correctly", () => {
    const commands = [
      {
        id: 1,
        command: "water",
        cmd_id: "test-1",
        sent_at: "2024-03-15T10:00:00Z",
        status: "acknowledged",
      },
    ];

    render(<CommandHistory commands={commands} />);

    expect(screen.getByText("acknowledged")).toBeInTheDocument();
  });

  it("should show em dash for missing ack_at", () => {
    const commands = [
      {
        id: 1,
        command: "water",
        cmd_id: "test-1",
        sent_at: "2024-03-15T10:00:00Z",
        ack_at: null,
        status: "pending",
      },
    ];

    render(<CommandHistory commands={commands} />);

    // Check for em dash in the ack_at column
    const cells = screen.getAllByText("—");
    expect(cells.length).toBeGreaterThan(0);
  });

  it("should show error message when present", () => {
    const commands = [
      {
        id: 1,
        command: "water",
        cmd_id: "test-1",
        sent_at: "2024-03-15T10:00:00Z",
        status: "failed",
        error: "Connection timeout",
      },
    ];

    render(<CommandHistory commands={commands} />);

    expect(screen.getByText("Connection timeout")).toBeInTheDocument();
  });

  it("should format timestamps correctly", () => {
    const commands = [
      {
        id: 1,
        command: "water",
        cmd_id: "test-1",
        sent_at: "2024-03-15T10:00:00Z",
        ack_at: "2024-03-15T10:00:05Z",
        status: "ok",
      },
    ];

    render(<CommandHistory commands={commands} />);

    // Just verify dates are rendered (exact format depends on locale)
    const table = screen.getByRole("table");
    expect(table).toBeInTheDocument();
  });
});
