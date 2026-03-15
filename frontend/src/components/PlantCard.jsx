import React from 'react';
import { Link } from 'react-router-dom';

function PlantCard({ plant }) {
  const { plant_id, name, location, state } = plant;
  const isOnline = state?.online || false;
  const lastSeen = state?.last_seen ? new Date(state.last_seen).toLocaleString() : 'Never';
  const moisture = state?.last_moisture ?? 'N/A';

  return (
    <Link to={`/plant/${plant_id}`} className="plant-card">
      <div className="plant-card-header">
        <h3>{name || plant_id}</h3>
        <span className={`status-badge ${isOnline ? 'online' : 'offline'}`}>
          {isOnline ? '● Online' : '○ Offline'}
        </span>
      </div>
      <div className="plant-card-body">
        {location && <p className="plant-location">📍 {location}</p>}
        <p className="plant-metric">
          <strong>Moisture:</strong> {moisture !== 'N/A' ? `${moisture}%` : moisture}
        </p>
        <p className="plant-last-seen">
          <small>Last seen: {lastSeen}</small>
        </p>
      </div>
    </Link>
  );
}

export default PlantCard;
