import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import CommandForm from "../components/CommandForm";
import * as apiClient from "../api/client";

// Mock the API client
vi.mock("../api/client");

describe("CommandForm", () => {
  let mockOnCommandSent;
  let mockOnError;
  let consoleErrorSpy;

  beforeEach(() => {
    mockOnCommandSent = vi.fn();
    mockOnError = vi.fn();
    vi.clearAllMocks();

    // Suppress console.error from expected error scenarios and React warnings
    consoleErrorSpy = vi
      .spyOn(console, "error")
      .mockImplementation((msg, ...args) => {
        if (typeof msg === "string") {
          // Silence expected error logs and React act warnings
          if (
            msg.includes("Failed to send command") ||
            msg.includes("Warning: An update to")
          ) {
            return;
          }
        }
        // Log other errors normally
        console.warn("Unexpected console.error:", msg, ...args);
      });
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
  });

  it("should render command form with default values", () => {
    render(
      <CommandForm
        plantId="test_plant_01"
        onCommandSent={mockOnCommandSent}
        onError={mockOnError}
      />
    );

    expect(screen.getByLabelText("Send Command:")).toBeInTheDocument();
    expect(screen.getByRole("combobox")).toHaveValue("water");
    expect(
      screen.getByRole("button", { name: /Send Command/i })
    ).toBeInTheDocument();
  });

  it("should have all command options in dropdown", () => {
    render(
      <CommandForm
        plantId="test_plant_01"
        onCommandSent={mockOnCommandSent}
        onError={mockOnError}
      />
    );

    const select = screen.getByRole("combobox");
    const options = select.querySelectorAll("option");

    expect(options).toHaveLength(1);
    expect(options[0]).toHaveValue("water");
  });

  it("should call onCommandSent on successful submission", async () => {
    const user = userEvent.setup();
    const mockResponse = {
      id: 1,
      command: "water",
      cmd_id: "test-123",
      status: "pending",
    };

    apiClient.sendCommand.mockResolvedValue(mockResponse);

    render(
      <CommandForm
        plantId="test_plant_01"
        onCommandSent={mockOnCommandSent}
        onError={mockOnError}
      />
    );

    const button = screen.getByRole("button", { name: /Send Command/i });
    await user.click(button);

    await waitFor(() => {
      expect(mockOnCommandSent).toHaveBeenCalledWith(mockResponse);
    });

    // Wait for all state updates to complete
    await waitFor(() => {
      expect(button).not.toBeDisabled();
    });
  });

  it("should disable form while sending", async () => {
    const user = userEvent.setup();

    apiClient.sendCommand.mockImplementation(
      () => new Promise((resolve) => setTimeout(resolve, 100))
    );

    render(
      <CommandForm
        plantId="test_plant_01"
        onCommandSent={mockOnCommandSent}
        onError={mockOnError}
      />
    );

    const button = screen.getByRole("button", { name: /Send Command/i });
    await user.click(button);

    // Button should show "Sending..." and be disabled
    await waitFor(() => {
      expect(screen.getByText("Sending...")).toBeInTheDocument();
      expect(button).toBeDisabled();
    });

    // Wait for sending to complete
    await waitFor(() => {
      expect(button).not.toBeDisabled();
    });
  });

  it("should call onError on failed submission", async () => {
    const user = userEvent.setup();
    const errorMessage = "Network error";

    apiClient.sendCommand.mockRejectedValue({
      response: { data: { error: errorMessage } },
    });

    render(
      <CommandForm
        plantId="test_plant_01"
        onCommandSent={mockOnCommandSent}
        onError={mockOnError}
      />
    );

    const button = screen.getByRole("button", { name: /Send Command/i });
    await user.click(button);

    await waitFor(() => {
      expect(mockOnError).toHaveBeenCalledWith(errorMessage);
    });

    // Wait for all state updates to complete
    await waitFor(() => {
      expect(button).not.toBeDisabled();
    });
  });
});
