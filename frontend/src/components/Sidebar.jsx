import React from 'react';
import { Link } from 'react-router-dom';
import './Sidebar.css';

const Sidebar = ({ plants }) => (
  <div className="sidebar">
    <div className="sidebar-logo">
      Planty<span>Three</span>
    </div>
    <div style={{ paddingLeft: 24, paddingBottom: 8 }}>
      <Link to="/new-plant" className="sidebar-add-btn">
        Add new plant
      </Link>
    </div>
    <div className="sidebar-plant-list">
      {plants.map((plant, idx) => (
        <div key={plant.id || idx} className="sidebar-plant-item">
          {plant.name}
        </div>
      ))}
    </div>
  </div>
);

export default Sidebar;
