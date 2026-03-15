import axios from 'axios';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

export const fetchPlants = async () => {
  const response = await apiClient.get('/plants/');
  return response.data;
};

export const fetchPlantDetail = async (plantId) => {
  const response = await apiClient.get(`/plants/${plantId}/`);
  return response.data;
};

export const fetchTelemetry = async (plantId, params = {}) => {
  const response = await apiClient.get(`/plants/${plantId}/telemetry/`, { params });
  return response.data;
};

export const fetchCommands = async (plantId) => {
  const response = await apiClient.get(`/plants/${plantId}/commands/`);
  return response.data;
};

export const sendCommand = async (plantId, command, args = {}) => {
  const response = await apiClient.post(`/plants/${plantId}/send_command/`, {
    command,
    args,
  });
  return response.data;
};

export const createPlant = async (plantData) => {
  const response = await apiClient.post('/plants/', plantData);
  return response.data;
};

export const updatePlant = async (plantId, plantData) => {
  const response = await apiClient.put(`/plants/${plantId}/`, plantData);
  return response.data;
};

export const deletePlant = async (plantId) => {
  const response = await apiClient.delete(`/plants/${plantId}/`);
  return response.data;
};

export default apiClient;
