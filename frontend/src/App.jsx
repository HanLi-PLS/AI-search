import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Home from './pages/Home';
import StockTracker from './pages/StockTracker';
import './App.css';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/stock-tracker" element={<StockTracker />} />
      </Routes>
    </Router>
  );
}

export default App;
