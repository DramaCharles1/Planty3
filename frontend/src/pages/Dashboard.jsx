import React, { useEffect, useState } from 'react';
import { fetchPlants, createPlant } from '../api/client';
import PlantCard from '../components/PlantCard';
import PlantForm from '../components/PlantForm';

const REFRESH_INTERVAL = 30000; // 30 seconds

function Dashboard() {
  const [plants, setPlants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [formError, setFormError] = useState(null);
  const [formSuccess, setFormSuccess] = useState(null);

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

  useEffect(() => {
    loadPlants();

    // Set up auto-refresh
    const intervalId = setInterval(loadPlants, REFRESH_INTERVAL);

    // Cleanup interval on unmount
    return () => clearInterval(intervalId);
  }, []);

  const handleAddPlant = async (plantData) => {
    try {
      setFormError(null);
      await createPlant(plantData);
      setFormSuccess('Plant added successfully!');
      setShowAddModal(false);
      // Reload plants
      await loadPlants();
      // Clear success message after 3 seconds
      setTimeout(() => setFormSuccess(null), 3000);
    } catch (err) {
      console.error('Failed to create plant:', err);
      if (err.response?.data) {
        // Extract validation errors from API response
        const errors = Object.entries(err.response.data)
          .map(([field, messages]) => `${field}: ${messages.join(', ')}`)
          .join('; ');
        setFormError(errors);
      } else {
        setFormError('Failed to create plant. Please try again.');
      }
    }
  };

  if (loading && plants.length === 0) {
    return <div className="loading">Loading plants...</div>;
  }

  if (error) {
    return <div className="error">{error}</div>;
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h2>All Plants</h2>
        <div>
          <button onClick={() => setShowAddModal(true)} className="btn btn-primary">
            Add Plant
          </button>
          {lastUpdate && (
            <span className="last-update" style={{ marginLeft: '1rem' }}>
              Last updated: {lastUpdate.toLocaleTimeString()}
            </span>
          )}
        </div>
      </div>

      {formSuccess && <div className="alert alert-success">{formSuccess}</div>}

      {plants.length === 0 ? (
        <div className="empty-state">
          No plants found. Click "Add Plant" to create your first plant.
        </div>
      ) : (
        <div className="plant-grid">
          {plants.map((plant) => (
            <PlantCard key={plant.plant_id} plant={plant} />
          ))}
        </div>
      )}

      {showAddModal && (
        <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Add New Plant</h2>
              <button
                className="modal-close"
                onClick={() => setShowAddModal(false)}
                aria-label="Close"
              >
                ×
              </button>
            </div>
            {formError && <div className="alert alert-error">{formError}</div>}
            <PlantForm
              onSubmit={handleAddPlant}
              onCancel={() => setShowAddModal(false)}
            />
          </div>
        </div>
      )}
    </div>
  );
}

export default Dashboard;
