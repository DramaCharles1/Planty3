/**
 * WebSocket client for real-time telemetry updates
 */

const WS_BASE_URL = 'ws://localhost:8000';

/**
 * Create a WebSocket connection for a plant's telemetry updates
 * @param {string} plantId - The plant ID to subscribe to
 * @param {function} onMessage - Callback function for telemetry updates
 * @param {function} onError - Callback function for errors
 * @param {function} onClose - Callback function for connection close
 * @returns {WebSocket} WebSocket connection object
 */
export function connectToPlantTelemetry(plantId, onMessage, onError, onClose) {
  const ws = new WebSocket(`${WS_BASE_URL}/ws/plants/${plantId}/telemetry/`);

  ws.onopen = () => {
    console.log(`WebSocket connected for plant: ${plantId}`);
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
    }
  };

  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
    if (onError) {
      onError(error);
    }
  };

  ws.onclose = (event) => {
    console.log(`WebSocket closed for plant: ${plantId}`, event);
    if (onClose) {
      onClose(event);
    }
  };

  return ws;
}

/**
 * Close a WebSocket connection safely
 * @param {WebSocket} ws - WebSocket connection to close
 */
export function disconnectWebSocket(ws) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.close();
  }
}
