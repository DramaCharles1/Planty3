import React, { useEffect, useState } from 'react';
import { fetchPlants } from '../api/client';
import PlantCard from '../components/PlantCard';

function Dashboard() {
  const [plants, setPlants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadPlants = async () => {
      try {
        setLoading(true);
        const data = await fetchPlants();
        setPlants(data.results || []);
      } catch (err) {
        console.error('Failed to load plants:', err);
        setError('Failed to load plants. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    loadPlants();
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
      <h2>All Plants</h2>
      <div className="plant-grid">
        {plants.map((plant) => (
          <PlantCard key={plant.plant_id} plant={plant} />
        ))}
      </div>
    </div>
  );
}

export default Dashboard;
