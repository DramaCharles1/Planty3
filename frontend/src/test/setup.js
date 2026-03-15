import "@testing-library/jest-dom";
import { vi } from "vitest";

// Mock Chart.js to avoid canvas issues in tests
vi.mock("chart.js", () => {
  const mockRegister = vi.fn();
  return {
    Chart: {
      register: mockRegister,
    },
    CategoryScale: vi.fn(),
    LinearScale: vi.fn(),
    PointElement: vi.fn(),
    LineElement: vi.fn(),
    Title: vi.fn(),
    Tooltip: vi.fn(),
    Legend: vi.fn(),
    TimeScale: vi.fn(),
    register: mockRegister,
  };
});

vi.mock("react-chartjs-2", () => ({
  Line: () => null,
}));
