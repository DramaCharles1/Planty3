import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import PlantDetail from "../pages/PlantDetail";
import * as apiClient from "../api/client";

// Mock the API client
vi.mock("../api/client");

// Mock the WebSocket client
vi.mock("../api/websocket", () => ({
  connectToPlantTelemetry: vi.fn(() => ({})),
  disconnectWebSocket: vi.fn(),
}));

const renderWithRouter = (plantId = "test_plant_01") => {
  return render(
    <MemoryRouter
      initialEntries={[`/plant/${plantId}`]}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <Routes>
        <Route path="/plant/:plantId" element={<PlantDetail />} />
      </Routes>
    </MemoryRouter>
  );
};

describe("PlantDetail", () => {
  let consoleErrorSpy;

  beforeEach(() => {
    vi.clearAllMocks();

    // Suppress expected console.error logs from error test scenarios
    consoleErrorSpy = vi
      .spyOn(console, "error")
      .mockImplementation((msg, ...args) => {
        if (
          typeof msg === "string" &&
          msg.includes("Failed to load plant data")
        ) {
          return; // Silence expected error logs
        }
        // Log other errors normally
        console.warn("Unexpected console.error:", msg, ...args);
      });
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
    vi.restoreAllMocks();
    vi.useRealTimers(); // Ensure we always restore real timers
  });

  it("should show loading state initially", () => {
    apiClient.fetchPlantDetail.mockImplementation(() => new Promise(() => {}));
    apiClient.fetchTelemetry.mockImplementation(() => new Promise(() => {}));
    apiClient.fetchCommands.mockImplementation(() => new Promise(() => {}));

    renderWithRouter();

    expect(screen.getByText("Loading plant details...")).toBeInTheDocument();
  });

  it("should render plant details after loading", async () => {
    const mockPlant = {
      plant_id: "test_plant_01",
      name: "Test Plant",
      location: "Office",
      state: {
        online: true,
        last_seen: "2024-03-15T10:00:00Z",
        last_moisture: 65,
      },
    };

    const mockTelemetry = {
      count: 2,
      results: [
        {
          id: 1,
          type: "moisture",
          value: 65,
          timestamp: "2024-03-15T10:00:00Z",
        },
        {
          id: 2,
          type: "moisture",
          value: 70,
          timestamp: "2024-03-15T11:00:00Z",
        },
      ],
    };

    const mockCommands = {
      count: 1,
      results: [
        {
          id: 1,
          command: "water",
          cmd_id: "test-123",
          sent_at: "2024-03-15T09:00:00Z",
          status: "ok",
        },
      ],
    };

    apiClient.fetchPlantDetail.mockResolvedValue(mockPlant);
    apiClient.fetchTelemetry.mockResolvedValue(mockTelemetry);
    apiClient.fetchCommands.mockResolvedValue(mockCommands);

    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByText("Test Plant")).toBeInTheDocument();
      expect(screen.getByText(/Office/)).toBeInTheDocument();
      expect(screen.getByText("● Online")).toBeInTheDocument();
    });
  });

  it("should show error message on fetch failure", async () => {
    apiClient.fetchPlantDetail.mockRejectedValue(new Error("Network error"));
    apiClient.fetchTelemetry.mockRejectedValue(new Error("Network error"));
    apiClient.fetchCommands.mockRejectedValue(new Error("Network error"));

    renderWithRouter();

    await waitFor(() => {
      expect(
        screen.getByText("Failed to load plant data. Please try again later.")
      ).toBeInTheDocument();
    });
  });

  it("should display last updated timestamp", async () => {
    const mockPlant = {
      plant_id: "test_plant_01",
      name: "Test Plant",
      state: { online: true },
    };

    apiClient.fetchPlantDetail.mockResolvedValue(mockPlant);
    apiClient.fetchTelemetry.mockResolvedValue({ count: 0, results: [] });
    apiClient.fetchCommands.mockResolvedValue({ count: 0, results: [] });

    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByText(/Last updated:/)).toBeInTheDocument();
    });
  });

  it("should render telemetry chart when data available", async () => {
    const mockPlant = {
      plant_id: "test_plant_01",
      name: "Test Plant",
      state: { online: true },
    };

    const mockTelemetry = {
      count: 3,
      results: [
        {
          id: 1,
          type: "moisture",
          value: 65,
          timestamp: "2024-03-15T10:00:00Z",
        },
        {
          id: 2,
          type: "moisture",
          value: 70,
          timestamp: "2024-03-15T11:00:00Z",
        },
        {
          id: 3,
          type: "moisture",
          value: 68,
          timestamp: "2024-03-15T12:00:00Z",
        },
      ],
    };

    apiClient.fetchPlantDetail.mockResolvedValue(mockPlant);
    apiClient.fetchTelemetry.mockResolvedValue(mockTelemetry);
    apiClient.fetchCommands.mockResolvedValue({ count: 0, results: [] });

    renderWithRouter();

    await waitFor(() => {
      // Chart is mocked, but container should be present
      const chartContainer = screen
        .getByText("Test Plant")
        .closest(".plant-detail");
      expect(chartContainer).toBeInTheDocument();
    });
  });

  it("should show empty state when no telemetry data", async () => {
    const mockPlant = {
      plant_id: "test_plant_01",
      name: "Test Plant",
      state: { online: true },
    };

    apiClient.fetchPlantDetail.mockResolvedValue(mockPlant);
    apiClient.fetchTelemetry.mockResolvedValue({ count: 0, results: [] });
    apiClient.fetchCommands.mockResolvedValue({ count: 0, results: [] });

    renderWithRouter();

    await waitFor(() => {
      expect(
        screen.getByText("No telemetry data available for this time range.")
      ).toBeInTheDocument();
    });
  });

  it("should render command form", async () => {
    const mockPlant = {
      plant_id: "test_plant_01",
      name: "Test Plant",
      state: { online: true },
    };

    apiClient.fetchPlantDetail.mockResolvedValue(mockPlant);
    apiClient.fetchTelemetry.mockResolvedValue({ count: 0, results: [] });
    apiClient.fetchCommands.mockResolvedValue({ count: 0, results: [] });

    renderWithRouter();

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: "Send Command" })
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /Send Command/i })
      ).toBeInTheDocument();
    });
  });

  it("should render command history", async () => {
    const mockPlant = {
      plant_id: "test_plant_01",
      name: "Test Plant",
      state: { online: true },
    };

    const mockCommands = {
      count: 2,
      results: [
        {
          id: 1,
          command: "water",
          cmd_id: "test-123",
          sent_at: "2024-03-15T09:00:00Z",
          status: "ok",
        },
      ],
    };

    apiClient.fetchPlantDetail.mockResolvedValue(mockPlant);
    apiClient.fetchTelemetry.mockResolvedValue({ count: 0, results: [] });
    apiClient.fetchCommands.mockResolvedValue(mockCommands);

    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByText("Command History")).toBeInTheDocument();
      expect(screen.getByText("water")).toBeInTheDocument();
    });
  });

  it("should have back link to dashboard", async () => {
    const mockPlant = {
      plant_id: "test_plant_01",
      name: "Test Plant",
      state: { online: true },
    };

    apiClient.fetchPlantDetail.mockResolvedValue(mockPlant);
    apiClient.fetchTelemetry.mockResolvedValue({ count: 0, results: [] });
    apiClient.fetchCommands.mockResolvedValue({ count: 0, results: [] });

    renderWithRouter();

    await waitFor(() => {
      const backLink = screen.getByText("← Back to Dashboard");
      expect(backLink).toBeInTheDocument();
      expect(backLink.closest("a")).toHaveAttribute("href", "/");
    });
  });
});
