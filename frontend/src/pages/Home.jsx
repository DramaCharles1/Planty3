import React, { useState } from 'react';
import Sidebar from '../components/Sidebar';
import QuickView from '../components/QuickView';

const initialPlants = [
  { id: 1, name: 'Green House', moisture: 110, temperature: 20 },
  { id: 2, name: 'Pallkrage', moisture: 200 }
];

const Home = () => {
  const [plants, setPlants] = useState(initialPlants);

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: '#fff' }}>
      <Sidebar plants={plants} />
      <div style={{ flex: 1, marginLeft: 220 }}>
        <QuickView plants={plants} />
      </div>
    </div>
  );
};

export default Home;
