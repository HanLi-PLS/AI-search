import { lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import './App.css';

// Code splitting: Lazy load route components
const Home = lazy(() => import('./pages/Home'));
const StockTracker = lazy(() => import('./pages/StockTracker'));
const StockDetail = lazy(() => import('./pages/StockDetail'));
const AISearch = lazy(() => import('./pages/AISearch'));

function App() {
  return (
    <Router>
      <Suspense fallback={<div className="loading-spinner">Loading...</div>}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/stock-tracker" element={<StockTracker />} />
          <Route path="/stock-tracker/:ticker" element={<StockDetail />} />
          <Route path="/ai-search" element={<AISearch />} />
        </Routes>
      </Suspense>
    </Router>
  );
}

export default App;
