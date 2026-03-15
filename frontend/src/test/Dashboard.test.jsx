import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import Dashboard from "../pages/Dashboard";
import * as apiClient from "../api/client";

// Mock the API client
vi.mock("../api/client");

const renderWithRouter = (component) => {
  return render(
    <BrowserRouter
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      {component}
    </BrowserRouter>
  );
};

describe("Dashboard", () => {
  let consoleErrorSpy;

  beforeEach(() => {
    vi.clearAllMocks();

    // Suppress expected console.error logs from error test scenarios
    consoleErrorSpy = vi
      .spyOn(console, "error")
      .mockImplementation((msg, ...args) => {
        if (typeof msg === "string" && msg.includes("Failed to load plants")) {
          return; // Silence expected error logs
        }
        // Log other errors normally
        console.warn("Unexpected console.error:", msg, ...args);
      });
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
    vi.restoreAllMocks();
  });

  it("should show loading state initially", () => {
    apiClient.fetchPlants.mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    renderWithRouter(<Dashboard />);

    expect(screen.getByText("Loading plants...")).toBeInTheDocument();
  });

  it("should render plants after loading", async () => {
    const mockPlants = {
      count: 2,
      results: [
        {
          plant_id: "plant1",
          name: "Plant 1",
          location: "Office",
          state: { online: true, last_moisture: 65 },
        },
        {
          plant_id: "plant2",
          name: "Plant 2",
          location: "Kitchen",
          state: { online: false, last_moisture: 45 },
        },
      ],
    };

    apiClient.fetchPlants.mockResolvedValue(mockPlants);

    renderWithRouter(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText("Plant 1")).toBeInTheDocument();
      expect(screen.getByText("Plant 2")).toBeInTheDocument();
    });
  });

  it("should show error message on fetch failure", async () => {
    apiClient.fetchPlants.mockRejectedValue(new Error("Network error"));

    renderWithRouter(<Dashboard />);

    await waitFor(() => {
      expect(
        screen.getByText("Failed to load plants. Please try again later.")
      ).toBeInTheDocument();
    });
  });

  it("should show empty state when no plants", async () => {
    apiClient.fetchPlants.mockResolvedValue({ count: 0, results: [] });

    renderWithRouter(<Dashboard />);

    await waitFor(() => {
      expect(
        screen.getByText(/No plants found.*to create your first plant/)
      ).toBeInTheDocument();
    });
  });

  it("should display last updated timestamp", async () => {
    const mockPlants = {
      count: 1,
      results: [
        {
          plant_id: "plant1",
          name: "Test Plant",
          state: { online: true },
        },
      ],
    };

    apiClient.fetchPlants.mockResolvedValue(mockPlants);

    renderWithRouter(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText(/Last updated:/)).toBeInTheDocument();
    });
  });

  it("should render plant grid with correct number of cards", async () => {
    const mockPlants = {
      count: 3,
      results: [
        { plant_id: "plant1", name: "Plant 1", state: { online: true } },
        { plant_id: "plant2", name: "Plant 2", state: { online: false } },
        { plant_id: "plant3", name: "Plant 3", state: { online: true } },
      ],
    };

    apiClient.fetchPlants.mockResolvedValue(mockPlants);

    renderWithRouter(<Dashboard />);

    await waitFor(() => {
      const links = screen.getAllByRole("link");
      expect(links).toHaveLength(3);
    });
  });
});
