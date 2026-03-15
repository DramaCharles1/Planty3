import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { fetchPlantDetail, fetchTelemetry, fetchCommands } from '../api/client';
import TelemetryChart from '../components/TelemetryChart';
import CommandHistory from '../components/CommandHistory';

function PlantDetail() {
  const { plantId } = useParams();
  const [plant, setPlant] = useState(null);
  const [telemetry, setTelemetry] = useState([]);
  const [commands, setCommands] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [timeRange, setTimeRange] = useState('1h');

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
      } catch (err) {
        console.error('Failed to load plant data:', err);
        setError('Failed to load plant data. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    loadPlantData();
  }, [plantId, timeRange]);

  const getHoursFromRange = (range) => {
    const rangeMap = {
      '1h': 1,
      '6h': 6,
      '24h': 24,
      '7d': 168,
    };
    return rangeMap[range] || 1;
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
        <span className={`status-badge ${isOnline ? 'online' : 'offline'}`}>
          {isOnline ? '● Online' : '○ Offline'}
        </span>
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
        <h3>Command History</h3>
        <CommandHistory commands={commands} />
      </div>
    </div>
  );
}

export default PlantDetail;
