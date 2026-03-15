import React, { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { fetchPlantDetail, fetchTelemetry, fetchCommands, updatePlant, deletePlant } from '../api/client';
import { connectToPlantTelemetry, disconnectWebSocket } from '../api/websocket';
import TelemetryChart from '../components/TelemetryChart';
import CommandHistory from '../components/CommandHistory';
import CommandForm from '../components/CommandForm';
import PlantForm from '../components/PlantForm';

const REFRESH_INTERVAL = 30000; // 30 seconds

function PlantDetail() {
  const { plantId } = useParams();
  const navigate = useNavigate();
  const [plant, setPlant] = useState(null);
  const [telemetry, setTelemetry] = useState([]);
  const [commands, setCommands] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [timeRange, setTimeRange] = useState('1h');
  const [lastUpdate, setLastUpdate] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [formError, setFormError] = useState(null);

  useEffect(() => {
    const loadPlantData = async () => {
      try {
        setLoading(true);
        const [plantData, telemetryData, commandsData] = await Promise.all([
          fetchPlantDetail(plantId),
          fetchTelemetry(plantId, { hours: getHoursFromRange(timeRange) }),
          fetchCommands(plantId),
        ]);
        setPlant(plantData);
        setTelemetry(telemetryData.results || []);
        setCommands(commandsData.results || []);
        setLastUpdate(new Date());
        setError(null);
      } catch (err) {
        console.error('Failed to load plant data:', err);
        setError('Failed to load plant data. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    loadPlantData();

    // Set up auto-refresh
    const intervalId = setInterval(loadPlantData, REFRESH_INTERVAL);

    // Cleanup interval on unmount
    return () => clearInterval(intervalId);
  }, [plantId, timeRange]);

  // WebSocket connection for real-time telemetry updates
  useEffect(() => {
    const handleTelemetryUpdate = (data) => {
      console.log('Received telemetry update:', data);
      
      // Update telemetry list with new data point
      setTelemetry((prevTelemetry) => {
        const newDataPoint = {
          timestamp: data.timestamp,
          value: data.value,
          type: data.metric,
        };
        
        // Add new data point and sort by timestamp (newest first)
        const updated = [newDataPoint, ...prevTelemetry];
        
        // Remove data points outside the current time range
        const hoursToKeep = getHoursFromRange(timeRange);
        const cutoffTime = new Date(Date.now() - hoursToKeep * 60 * 60 * 1000);
        
        return updated.filter((point) => new Date(point.timestamp) > cutoffTime);
      });

      // Update plant state with latest moisture value
      if (data.metric === 'moisture' && plant) {
        setPlant((prevPlant) => ({
          ...prevPlant,
          state: {
            ...prevPlant.state,
            last_moisture: data.value,
          },
        }));
      }

      setLastUpdate(new Date());
    };

    const handleWsError = (error) => {
      console.error('WebSocket error:', error);
      setWsConnected(false);
    };

    const handleWsClose = () => {
      console.log('WebSocket closed');
      setWsConnected(false);
    };

    // Connect to WebSocket
    const ws = connectToPlantTelemetry(plantId, handleTelemetryUpdate, handleWsError, handleWsClose);
    setWsConnected(true);

    // Cleanup on unmount
    return () => {
      disconnectWebSocket(ws);
      setWsConnected(false);
    };
  }, [plantId, timeRange, plant]);

  const getHoursFromRange = (range) => {
    const rangeMap = {
      '1h': 1,
      '6h': 6,
      '24h': 24,
      '7d': 168,
    };
    return rangeMap[range] || 1;
  };

  const handleCommandSent = async (commandLog) => {
    setSuccessMessage(`Command "${commandLog.command}" sent successfully!`);
    setErrorMessage(null);

    // Auto-clear success message after 5 seconds
    setTimeout(() => setSuccessMessage(null), 5000);

    // Refresh command history
    try {
      const commandsData = await fetchCommands(plantId);
      setCommands(commandsData.results || []);
    } catch (err) {
      console.error('Failed to refresh commands:', err);
    }
  };

  const handleCommandError = (error) => {
    setErrorMessage(error);
    setSuccessMessage(null);

    // Auto-clear error message after 5 seconds
    setTimeout(() => setErrorMessage(null), 5000);
  };

  const handleEditPlant = async (plantData) => {
    try {
      setFormError(null);
      await updatePlant(plantId, plantData);
      setSuccessMessage('Plant updated successfully!');
      setShowEditModal(false);
      // Reload plant data
      const plantData_ = await fetchPlantDetail(plantId);
      setPlant(plantData_);
      // Auto-clear success message after 3 seconds
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      console.error('Failed to update plant:', err);
      if (err.response?.data) {
        const errors = Object.entries(err.response.data)
          .map(([field, messages]) => `${field}: ${messages.join(', ')}`)
          .join('; ');
        setFormError(errors);
      } else {
        setFormError('Failed to update plant. Please try again.');
      }
    }
  };

  const handleDeletePlant = async () => {
    try {
      await deletePlant(plantId);
      navigate('/');
    } catch (err) {
      console.error('Failed to delete plant:', err);
      setErrorMessage('Failed to delete plant. Please try again.');
      setShowDeleteModal(false);
      setTimeout(() => setErrorMessage(null), 5000);
    }
  };

  if (loading) {
    return <div className="loading">Loading plant details...</div>;
  }

  if (error) {
    return <div className="error">{error}</div>;
  }

  if (!plant) {
    return <div className="error">Plant not found.</div>;
  }

  const isOnline = plant.state?.online || false;
  const lastSeen = plant.state?.last_seen
    ? new Date(plant.state.last_seen).toLocaleString()
    : 'Never';
  const moisture = plant.state?.last_moisture ?? 'N/A';

  return (
    <div className="plant-detail">
      <Link to="/" className="back-link">
        ← Back to Dashboard
      </Link>

      <div className="plant-header">
        <h2>{plant.name || plant.plant_id}</h2>
        <div className="plant-header-right">
          <button onClick={() => setShowEditModal(true)} className="btn btn-secondary">
            Edit
          </button>
          <button onClick={() => setShowDeleteModal(true)} className="btn btn-danger">
            Delete
          </button>
          <span className={`status-badge ${isOnline ? 'online' : 'offline'}`}>
            {isOnline ? '● Online' : '○ Offline'}
          </span>
          {wsConnected && (
            <span className="ws-indicator" title="Real-time updates active">
              🔴 Live
            </span>
          )}
          {lastUpdate && (
            <span className="last-update">
              Last updated: {lastUpdate.toLocaleTimeString()}
            </span>
          )}
        </div>
      </div>

      <div className="plant-info">
        <p>
          <strong>Plant ID:</strong> {plant.plant_id}
        </p>
        {plant.location && (
          <p>
            <strong>Location:</strong> {plant.location}
          </p>
        )}
        <p>
          <strong>Last Seen:</strong> {lastSeen}
        </p>
        <p>
          <strong>Current Moisture:</strong> {moisture !== 'N/A' ? `${moisture}%` : moisture}
        </p>
      </div>

      {successMessage && <div className="alert alert-success">{successMessage}</div>}
      {errorMessage && <div className="alert alert-error">{errorMessage}</div>}

      <div className="telemetry-section">
        <div className="section-header">
          <h3>Telemetry</h3>
          <div className="time-range-selector">
            <label>Time Range: </label>
            <select value={timeRange} onChange={(e) => setTimeRange(e.target.value)}>
              <option value="1h">Last Hour</option>
              <option value="6h">Last 6 Hours</option>
              <option value="24h">Last 24 Hours</option>
              <option value="7d">Last 7 Days</option>
            </select>
          </div>
        </div>
        {telemetry.length > 0 ? (
          <TelemetryChart telemetryData={telemetry} metricType="moisture" />
        ) : (
          <div className="empty-state">No telemetry data available for this time range.</div>
        )}
      </div>

      <div className="commands-section">
        <h3>Send Command</h3>
        <CommandForm
          plantId={plantId}
          onCommandSent={handleCommandSent}
          onError={handleCommandError}
        />
      </div>

      <div className="commands-section">
        <h3>Command History</h3>
        <CommandHistory commands={commands} />
      </div>

      {showEditModal && (
        <div className="modal-overlay" onClick={() => setShowEditModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Edit Plant</h2>
              <button
                className="modal-close"
                onClick={() => setShowEditModal(false)}
                aria-label="Close"
              >
                ×
              </button>
            </div>
            {formError && <div className="alert alert-error">{formError}</div>}
            <PlantForm
              plant={plant}
              onSubmit={handleEditPlant}
              onCancel={() => setShowEditModal(false)}
            />
          </div>
        </div>
      )}

      {showDeleteModal && (
        <div className="modal-overlay" onClick={() => setShowDeleteModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Delete Plant</h2>
              <button
                className="modal-close"
                onClick={() => setShowDeleteModal(false)}
                aria-label="Close"
              >
                ×
              </button>
            </div>
            <div className="confirmation-dialog">
              <p>
                Are you sure you want to delete <strong>{plant.name || plant.plant_id}</strong>?
                This will permanently remove all telemetry data and command history.
              </p>
              <div className="confirmation-actions">
                <button onClick={handleDeletePlant} className="btn btn-danger">
                  Delete
                </button>
                <button onClick={() => setShowDeleteModal(false)} className="btn btn-secondary">
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default PlantDetail;
