import { BrowserRouter, Routes, Route } from 'react-router-dom';
import './index.css';
import Home from './pages/Home.jsx';
import NewPlant from './pages/NewPlant.jsx';

function App() {

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/new-plant" element={<NewPlant />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
