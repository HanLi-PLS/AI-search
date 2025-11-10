import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Home from './pages/Home';
import StockTracker from './pages/StockTracker';
import AISearch from './pages/AISearch';
import './App.css';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/stock-tracker" element={<StockTracker />} />
        <Route path="/ai-search" element={<AISearch />} />
      </Routes>
    </Router>
  );
}

export default App;
