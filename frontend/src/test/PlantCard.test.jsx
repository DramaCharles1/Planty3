import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import PlantCard from "../components/PlantCard";

// Helper to render with router
const renderWithRouter = (component) => {
  return render(
    <BrowserRouter
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      {component}
    </BrowserRouter>
  );
};

describe("PlantCard", () => {
  it("should render plant card with all data", () => {
    const plant = {
      plant_id: "test_plant_01",
      name: "Test Plant",
      location: "Living Room",
      state: {
        online: true,
        last_seen: "2024-03-15T10:00:00Z",
        last_moisture: 65,
      },
    };

    renderWithRouter(<PlantCard plant={plant} />);

    expect(screen.getByText("Test Plant")).toBeInTheDocument();
    expect(screen.getByText("📍 Living Room")).toBeInTheDocument();
    expect(screen.getByText(/Moisture:/)).toBeInTheDocument();
    expect(screen.getByText(/65%/)).toBeInTheDocument();
    expect(screen.getByText("● Online")).toBeInTheDocument();
  });

  it("should show plant_id when name is missing", () => {
    const plant = {
      plant_id: "test_plant_02",
      state: {
        online: false,
      },
    };

    renderWithRouter(<PlantCard plant={plant} />);

    expect(screen.getByText("test_plant_02")).toBeInTheDocument();
  });

  it("should show offline status", () => {
    const plant = {
      plant_id: "test_plant_03",
      name: "Offline Plant",
      state: {
        online: false,
      },
    };

    renderWithRouter(<PlantCard plant={plant} />);

    expect(screen.getByText("○ Offline")).toBeInTheDocument();
  });

  it("should show N/A for missing moisture data", () => {
    const plant = {
      plant_id: "test_plant_04",
      name: "No Moisture Plant",
      state: {},
    };

    renderWithRouter(<PlantCard plant={plant} />);

    expect(screen.getByText(/Moisture:/)).toBeInTheDocument();
    expect(screen.getByText(/N\/A/)).toBeInTheDocument();
  });

  it('should show "Never" for last seen when no timestamp', () => {
    const plant = {
      plant_id: "test_plant_05",
      name: "New Plant",
      state: {},
    };

    renderWithRouter(<PlantCard plant={plant} />);

    expect(screen.getByText(/Last seen: Never/)).toBeInTheDocument();
  });

  it("should not render location if not provided", () => {
    const plant = {
      plant_id: "test_plant_06",
      name: "No Location Plant",
      state: {
        online: true,
      },
    };

    renderWithRouter(<PlantCard plant={plant} />);

    expect(screen.queryByText(/📍/)).not.toBeInTheDocument();
  });

  it("should render as a link to plant detail page", () => {
    const plant = {
      plant_id: "test_plant_07",
      name: "Link Test Plant",
      state: { online: true },
    };

    renderWithRouter(<PlantCard plant={plant} />);

    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "/plant/test_plant_07");
  });
});
