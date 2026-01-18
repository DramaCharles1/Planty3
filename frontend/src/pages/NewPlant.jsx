import React, { useState } from 'react';
import '../components/NewPlant.css';

const FEATURE_OPTIONS = [
  { value: 'moisture', label: 'Read moisture' },
  { value: 'temperature', label: 'Read temperature' },
  { value: 'water', label: 'Water' },
];

const NewPlant = () => {
  const [name, setName] = useState('');
  const [features, setFeatures] = useState([
    FEATURE_OPTIONS[0],
    FEATURE_OPTIONS[1],
    FEATURE_OPTIONS[2],
  ]);
  const [selectedFeature, setSelectedFeature] = useState(FEATURE_OPTIONS[0].value);

  const handleAddFeature = () => {
    const feature = FEATURE_OPTIONS.find(f => f.value === selectedFeature);
    if (feature && !features.some(f => f.value === feature.value)) {
      setFeatures([...features, feature]);
    }
  };

  const handleRemoveFeature = (value) => {
    setFeatures(features.filter(f => f.value !== value));
  };

  const handleSave = () => {
    // Save logic here
    alert(`Saved plant: ${name} with features: ${features.map(f => f.label).join(', ')}`);
  };

  return (
    <div className="newplant-container">
      <h1 className="newplant-title">New plant</h1>
      <div className="newplant-row">
        <label className="newplant-label">Name:</label>
        <input
          className="newplant-input"
          type="text"
          value={name}
          onChange={e => setName(e.target.value)}
          placeholder="Text box"
        />
      </div>
      <div className="newplant-row">
        <label className="newplant-label">Add new feature:</label>
        <select
          className="newplant-select"
          value={selectedFeature}
          onChange={e => setSelectedFeature(e.target.value)}
        >
          {FEATURE_OPTIONS.map(option => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
        <button className="newplant-btn" onClick={handleAddFeature}>Add button</button>
      </div>
      <div className="newplant-row">
        <label className="newplant-label">Features:</label>
        <div className="newplant-features">
          {features.map(feature => (
            <div className="newplant-feature-row" key={feature.value}>
              <button className="newplant-btn feature-btn">{feature.label}</button>
              <button className="newplant-btn remove-btn" onClick={() => handleRemoveFeature(feature.value)}>Remove button</button>
            </div>
          ))}
        </div>
      </div>
      <div className="newplant-row">
        <button className="newplant-btn save-btn" onClick={handleSave}>Save button</button>
      </div>
    </div>
  );
};

export default NewPlant;
