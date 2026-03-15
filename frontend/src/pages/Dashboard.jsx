import React, { useEffect, useState } from 'react';
import { fetchPlants } from '../api/client';
import PlantCard from '../components/PlantCard';

const REFRESH_INTERVAL = 30000; // 30 seconds

function Dashboard() {
  const [plants, setPlants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);

  useEffect(() => {
    const loadPlants = async () => {
      try {
        setLoading(true);
        const data = await fetchPlants();
        setPlants(data.results || []);
        setLastUpdate(new Date());
        setError(null);
      } catch (err) {
        console.error('Failed to load plants:', err);
        setError('Failed to load plants. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    loadPlants();

    // Set up auto-refresh
    const intervalId = setInterval(loadPlants, REFRESH_INTERVAL);

    // Cleanup interval on unmount
    return () => clearInterval(intervalId);
  }, []);

  if (loading) {
    return <div className="loading">Loading plants...</div>;
  }

  if (error) {
    return <div className="error">{error}</div>;
  }

  if (plants.length === 0) {
    return <div className="empty-state">No plants found. Add plants in Django Admin.</div>;
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h2>All Plants</h2>
        {lastUpdate && (
          <span className="last-update">
            Last updated: {lastUpdate.toLocaleTimeString()}
          </span>
        )}
      </div>
      <div className="plant-grid">
        {plants.map((plant) => (
          <PlantCard key={plant.plant_id} plant={plant} />
        ))}
      </div>
    </div>
  );
}

export default Dashboard;
