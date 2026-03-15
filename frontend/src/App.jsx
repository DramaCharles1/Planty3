import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import PlantDetail from './pages/PlantDetail';

function App() {
  return (
    <Router>
      <div className="app">
        <header className="app-header">
          <Link to="/" className="app-title">
            <h1>🌱 Planty3 Dashboard</h1>
          </Link>
        </header>
        <main className="app-main">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/plant/:plantId" element={<PlantDetail />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
