import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Dashboard from '../pages/Dashboard';
import * as apiClient from '../api/client';

// Mock the API client
vi.mock('../api/client');

const renderWithRouter = (component) => {
  return render(<BrowserRouter>{component}</BrowserRouter>);
};

describe('Dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should show loading state initially', () => {
    apiClient.fetchPlants.mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    renderWithRouter(<Dashboard />);

    expect(screen.getByText('Loading plants...')).toBeInTheDocument();
  });

  it('should render plants after loading', async () => {
    const mockPlants = {
      count: 2,
      results: [
        {
          plant_id: 'plant1',
          name: 'Plant 1',
          location: 'Office',
          state: { online: true, last_moisture: 65 },
        },
        {
          plant_id: 'plant2',
          name: 'Plant 2',
          location: 'Kitchen',
          state: { online: false, last_moisture: 45 },
        },
      ],
    };

    apiClient.fetchPlants.mockResolvedValue(mockPlants);

    renderWithRouter(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText('Plant 1')).toBeInTheDocument();
      expect(screen.getByText('Plant 2')).toBeInTheDocument();
    });
  });

  it('should show error message on fetch failure', async () => {
    apiClient.fetchPlants.mockRejectedValue(new Error('Network error'));

    renderWithRouter(<Dashboard />);

    await waitFor(() => {
      expect(
        screen.getByText('Failed to load plants. Please try again later.')
      ).toBeInTheDocument();
    });
  });

  it('should show empty state when no plants', async () => {
    apiClient.fetchPlants.mockResolvedValue({ count: 0, results: [] });

    renderWithRouter(<Dashboard />);

    await waitFor(() => {
      expect(
        screen.getByText('No plants found. Add plants in Django Admin.')
      ).toBeInTheDocument();
    });
  });

  it('should display last updated timestamp', async () => {
    const mockPlants = {
      count: 1,
      results: [
        {
          plant_id: 'plant1',
          name: 'Test Plant',
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

  it('should auto-refresh every 30 seconds', async () => {
    vi.useFakeTimers();
    
    const mockPlants = {
      count: 1,
      results: [
        {
          plant_id: 'plant1',
          name: 'Test Plant',
          state: { online: true },
        },
      ],
    };

    apiClient.fetchPlants.mockResolvedValue(mockPlants);

    renderWithRouter(<Dashboard />);

    // Wait for initial load
    await waitFor(() => {
      expect(screen.getByText('Test Plant')).toBeInTheDocument();
    });

    expect(apiClient.fetchPlants).toHaveBeenCalledTimes(1);

    // Fast-forward 30 seconds
    vi.advanceTimersByTime(30000);

    await waitFor(() => {
      expect(apiClient.fetchPlants).toHaveBeenCalledTimes(2);
    });
    
    vi.useRealTimers();
  });

  it('should cleanup interval on unmount', async () => {
    vi.useFakeTimers();
    
    const mockPlants = {
      count: 1,
      results: [{ plant_id: 'plant1', name: 'Test Plant', state: {} }],
    };

    apiClient.fetchPlants.mockResolvedValue(mockPlants);

    const { unmount } = renderWithRouter(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText('Test Plant')).toBeInTheDocument();
    });

    const callCountBeforeUnmount = apiClient.fetchPlants.mock.calls.length;

    unmount();

    // Advance time after unmount
    vi.advanceTimersByTime(30000);

    // Should not call fetchPlants after unmount
    expect(apiClient.fetchPlants).toHaveBeenCalledTimes(callCountBeforeUnmount);
    
    vi.useRealTimers();
  });

  it('should render plant grid with correct number of cards', async () => {
    const mockPlants = {
      count: 3,
      results: [
        { plant_id: 'plant1', name: 'Plant 1', state: { online: true } },
        { plant_id: 'plant2', name: 'Plant 2', state: { online: false } },
        { plant_id: 'plant3', name: 'Plant 3', state: { online: true } },
      ],
    };

    apiClient.fetchPlants.mockResolvedValue(mockPlants);

    renderWithRouter(<Dashboard />);

    await waitFor(() => {
      const links = screen.getAllByRole('link');
      expect(links).toHaveLength(3);
    });
  });
});
