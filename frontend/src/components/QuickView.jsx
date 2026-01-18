import React from 'react';
import './QuickView.css';

const QuickView = ({ plants }) => (
  <div className="quickview-container">
    <h1 className="quickview-title">Quick view</h1>
    {plants.map((plant, idx) => (
      <div key={plant.id || idx} className="quickview-plant">
        <div className="quickview-plant-name">
          {plant.name}:
        </div>
        <div className="quickview-plant-data">
          Communication: OK<br />
          Moisture: {plant.moisture}<br />
          {plant.temperature !== undefined && (
            <>Temperature: {plant.temperature} degrees<br /></>
          )}
        </div>
      </div>
    ))}
  </div>
);

export default QuickView;
