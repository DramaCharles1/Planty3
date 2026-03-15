import { describe, it, expect, beforeEach, vi } from 'vitest';

// Create mock functions
const mockGet = vi.fn();
const mockPost = vi.fn();

// Mock axios module
vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      get: mockGet,
      post: mockPost,
    })),
  },
}));

// Import after mocking
const {
  fetchPlants,
  fetchPlantDetail,
  fetchTelemetry,
  fetchCommands,
  sendCommand,
} = await import('../api/client');

describe('API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('fetchPlants', () => {
    it('should fetch plants list', async () => {
      const mockData = {
        count: 2,
        results: [
          { plant_id: 'plant1', name: 'Plant 1', state: { online: true } },
          { plant_id: 'plant2', name: 'Plant 2', state: { online: false } },
        ],
      };

      mockGet.mockResolvedValue({ data: mockData });

      const result = await fetchPlants();

      expect(result).toEqual(mockData);
      expect(mockGet).toHaveBeenCalledWith('/plants/');
    });

    it('should handle errors when fetching plants', async () => {
      mockGet.mockRejectedValue(new Error('Network error'));

      await expect(fetchPlants()).rejects.toThrow('Network error');
    });
  });

  describe('fetchPlantDetail', () => {
    it('should fetch plant detail by ID', async () => {
      const mockData = {
        plant_id: 'plant1',
        name: 'Test Plant',
        location: 'Office',
        state: { online: true, last_moisture: 65 },
      };

      mockGet.mockResolvedValue({ data: mockData });

      const result = await fetchPlantDetail('plant1');

      expect(result).toEqual(mockData);
      expect(mockGet).toHaveBeenCalledWith('/plants/plant1/');
    });
  });

  describe('fetchTelemetry', () => {
    it('should fetch telemetry with params', async () => {
      const mockData = {
        count: 10,
        results: [
          { id: 1, type: 'moisture', value: 65, timestamp: '2024-03-15T10:00:00Z' },
          { id: 2, type: 'moisture', value: 70, timestamp: '2024-03-15T11:00:00Z' },
        ],
      };

      mockGet.mockResolvedValue({ data: mockData });

      const result = await fetchTelemetry('plant1', { hours: 24 });

      expect(result).toEqual(mockData);
      expect(mockGet).toHaveBeenCalledWith('/plants/plant1/telemetry/', {
        params: { hours: 24 },
      });
    });

    it('should fetch telemetry without params', async () => {
      const mockData = { count: 0, results: [] };

      mockGet.mockResolvedValue({ data: mockData });

      const result = await fetchTelemetry('plant1');

      expect(result).toEqual(mockData);
    });
  });

  describe('fetchCommands', () => {
    it('should fetch command history', async () => {
      const mockData = {
        count: 3,
        results: [
          {
            id: 1,
            command: 'water',
            cmd_id: 'abc-123',
            sent_at: '2024-03-15T10:00:00Z',
            status: 'ok',
          },
          {
            id: 2,
            command: 'calibrate',
            cmd_id: 'def-456',
            sent_at: '2024-03-15T09:00:00Z',
            status: 'pending',
          },
        ],
      };

      mockGet.mockResolvedValue({ data: mockData });

      const result = await fetchCommands('plant1');

      expect(result).toEqual(mockData);
      expect(mockGet).toHaveBeenCalledWith('/plants/plant1/commands/');
    });
  });

  describe('sendCommand', () => {
    it('should send command with args', async () => {
      const mockResponse = {
        id: 10,
        command: 'water',
        cmd_id: 'xyz-789',
        sent_at: '2024-03-15T12:00:00Z',
        status: 'pending',
      };

      mockPost.mockResolvedValue({ data: mockResponse });

      const result = await sendCommand('plant1', 'water', { duration: 10 });

      expect(result).toEqual(mockResponse);
      expect(mockPost).toHaveBeenCalledWith('/plants/plant1/send_command/', {
        command: 'water',
        args: { duration: 10 },
      });
    });

    it('should send command without args', async () => {
      const mockResponse = {
        id: 11,
        command: 'reset',
        cmd_id: 'rst-999',
        sent_at: '2024-03-15T13:00:00Z',
        status: 'pending',
      };

      mockPost.mockResolvedValue({ data: mockResponse });

      const result = await sendCommand('plant1', 'reset');

      expect(result).toEqual(mockResponse);
      expect(mockPost).toHaveBeenCalledWith('/plants/plant1/send_command/', {
        command: 'reset',
        args: {},
      });
    });

    it('should handle errors when sending command', async () => {
      mockPost.mockRejectedValue(new Error('Server error'));

      await expect(sendCommand('plant1', 'water')).rejects.toThrow('Server error');
    });
  });
});
