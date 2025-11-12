import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { stockAPI } from '../services/api';
import StockCard from '../components/StockCard';
import './StockTracker.css';

function StockTracker() {
  const navigate = useNavigate();
  const [stockData, setStockData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState('name'); // 'name', 'price', 'change'
  const [upcomingIPOs, setUpcomingIPOs] = useState([]);
  const [showIPOs, setShowIPOs] = useState(false);

  useEffect(() => {
    fetchStockData();
    fetchUpcomingIPOs();
  }, []);

  const fetchStockData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await stockAPI.getAllPrices();
      setStockData(data);
    } catch (err) {
      setError('Failed to fetch stock data. Please make sure the backend is running.');
      console.error('Error fetching stock data:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchUpcomingIPOs = async () => {
    try {
      const data = await stockAPI.getUpcomingIPOs();
      setUpcomingIPOs(data);
    } catch (err) {
      console.error('Error fetching upcoming IPOs:', err);
    }
  };

  // Memoize filtered and sorted stocks to avoid duplicate calculations
  const filteredAndSortedStocks = useMemo(() => {
    let filtered = stockData.filter(
      (stock) =>
        stock.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        stock.ticker.toLowerCase().includes(searchTerm.toLowerCase())
    );

    // Sort stocks
    filtered.sort((a, b) => {
      if (sortBy === 'name') {
        return a.name.localeCompare(b.name);
      } else if (sortBy === 'price') {
        return (b.current_price || 0) - (a.current_price || 0);
      } else if (sortBy === 'change') {
        return (b.change_percent || 0) - (a.change_percent || 0);
      }
      return 0;
    });

    return filtered;
  }, [stockData, searchTerm, sortBy]);

  return (
    <div className="stock-tracker-container">
      <header className="tracker-header">
        <button className="back-button" onClick={() => navigate('/')}>
          ← Back to Home
        </button>
        <h1>HKEX 18A Biotech Stock Tracker</h1>
        <p className="header-subtitle">Real-time tracking of Hong Kong biotech companies</p>
      </header>

      <div className="controls-section">
        <div className="search-box">
          <input
            type="text"
            placeholder="Search by company name or ticker..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
        </div>

        <div className="sort-controls">
          <label>Sort by:</label>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="sort-select"
          >
            <option value="name">Company Name</option>
            <option value="price">Price (High to Low)</option>
            <option value="change">Change % (High to Low)</option>
          </select>
        </div>

        <button onClick={fetchStockData} className="refresh-button">
          🔄 Refresh
        </button>
      </div>

      <div className="stats-bar">
        <div className="stat">
          <span className="stat-label">Total Companies:</span>
          <span className="stat-value">{stockData.length}</span>
        </div>
        <div className="stat">
          <span className="stat-label">Market:</span>
          <span className="stat-value">HKEX 18A</span>
        </div>
        {upcomingIPOs && upcomingIPOs.length > 0 && (
          <div className="stat">
            <span className="stat-label">Upcoming IPOs:</span>
            <span className="stat-value">{upcomingIPOs.length}</span>
          </div>
        )}
      </div>

      {upcomingIPOs && upcomingIPOs.length > 0 && (
        <div className="ipo-section">
          <button
            className="ipo-toggle-button"
            onClick={() => setShowIPOs(!showIPOs)}
          >
            {showIPOs ? '▼' : '▶'} Upcoming HKEX 18A Biotech IPOs ({upcomingIPOs.length})
          </button>
          {showIPOs && (
            <div className="ipo-list">
              {upcomingIPOs.map((ipo, index) => (
                <div key={index} className="ipo-card">
                  <div className="ipo-header">
                    <h4>{ipo.company_name}</h4>
                    <span className="ipo-date">{ipo.expected_date || 'TBA'}</span>
                  </div>
                  <div className="ipo-details">
                    {ipo.price_range && (
                      <div className="ipo-detail">
                        <span className="detail-label">Price Range:</span>
                        <span className="detail-value">{ipo.price_range}</span>
                      </div>
                    )}
                    {ipo.description && (
                      <p className="ipo-description">{ipo.description}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {loading && (
        <div className="loading-container">
          <div className="spinner"></div>
          <p>Loading stock data...</p>
        </div>
      )}

      {error && (
        <div className="error-container">
          <p className="error-message">{error}</p>
          <button onClick={fetchStockData} className="retry-button">
            Retry
          </button>
        </div>
      )}

      {!loading && !error && (
        <div className="stocks-grid">
          {filteredAndSortedStocks.map((stock) => (
            <StockCard key={stock.ticker} stock={stock} />
          ))}
          {filteredAndSortedStocks.length === 0 && (
            <div className="no-results">
              <p>No stocks found matching "{searchTerm}"</p>
            </div>
          )}
        </div>
      )}

      <footer className="tracker-footer">
        <p>
          Data provided by Yahoo Finance via yfinance library. Last updated:{' '}
          {new Date().toLocaleString()}
        </p>
        <p className="disclaimer">
          Disclaimer: This is for informational purposes only. Not financial advice.
        </p>
      </footer>
    </div>
  );
}

export default StockTracker;
