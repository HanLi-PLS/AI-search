import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { stockAPI } from '../services/api';
import StockCard from '../components/StockCard';
import './StockTracker.css';

function StockTracker() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('hkex'); // 'hkex', 'portfolio', 'ipo'
  const [stockData, setStockData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState('name'); // 'name', 'price', 'change'
  const [upcomingIPOs, setUpcomingIPOs] = useState([]);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Cache keys
  const CACHE_KEY = 'hkex_stock_data';
  const CACHE_TIMESTAMP_KEY = 'hkex_stock_data_timestamp';
  const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes in milliseconds

  useEffect(() => {
    // Try to load cached data first
    const cachedData = localStorage.getItem(CACHE_KEY);
    const cachedTimestamp = localStorage.getItem(CACHE_TIMESTAMP_KEY);

    if (cachedData && cachedTimestamp) {
      const cacheAge = Date.now() - parseInt(cachedTimestamp);
      if (cacheAge < CACHE_DURATION) {
        // Use cached data if it's less than 5 minutes old
        const parsed = JSON.parse(cachedData);
        setStockData(parsed);
        setLastUpdated(new Date(parseInt(cachedTimestamp)));
        setLoading(false);
        console.log('Using cached stock data, age:', Math.round(cacheAge / 1000), 'seconds');
        return; // Don't fetch if cache is fresh
      }
    }

    // No cache or cache is stale, fetch fresh data
    fetchStockData();
    fetchUpcomingIPOs();
  }, []);

  const fetchStockData = async (isManualRefresh = false) => {
    try {
      // If we have cached data and this is a background refresh, don't show loading spinner
      const hasCachedData = stockData.length > 0;

      if (!hasCachedData) {
        setLoading(true);
      } else if (isManualRefresh) {
        setIsRefreshing(true);
      }

      setError(null);
      const data = await stockAPI.getAllPrices();
      setStockData(data);

      // Cache the data
      const timestamp = Date.now();
      localStorage.setItem(CACHE_KEY, JSON.stringify(data));
      localStorage.setItem(CACHE_TIMESTAMP_KEY, timestamp.toString());
      setLastUpdated(new Date(timestamp));

      console.log('Fetched fresh stock data and cached it');
    } catch (err) {
      setError('Failed to fetch stock data. Please make sure the backend is running.');
      console.error('Error fetching stock data:', err);
    } finally {
      setLoading(false);
      setIsRefreshing(false);
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
        <h1>Public Market Tracker</h1>
        <p className="header-subtitle">Track biotech stocks, portfolio companies, and IPO listings</p>
      </header>

      {/* Tab Navigation */}
      <div className="tab-navigation">
        <button
          className={`tab-button ${activeTab === 'hkex' ? 'active' : ''}`}
          onClick={() => setActiveTab('hkex')}
        >
          📊 HKEX 18A Biotech
        </button>
        <button
          className={`tab-button ${activeTab === 'portfolio' ? 'active' : ''}`}
          onClick={() => setActiveTab('portfolio')}
        >
          💼 Portfolio Companies
        </button>
        <button
          className={`tab-button ${activeTab === 'ipo' ? 'active' : ''}`}
          onClick={() => setActiveTab('ipo')}
        >
          🚀 IPO Listings
        </button>
      </div>

      {/* HKEX 18A Biotech Tab */}
      {activeTab === 'hkex' && (
        <>
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

            <button
              onClick={() => fetchStockData(true)}
              className="refresh-button"
              disabled={isRefreshing}
            >
              {isRefreshing ? '🔄 Refreshing...' : '🔄 Refresh'}
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
            {lastUpdated && (
              <div className="stat">
                <span className="stat-label">Last Updated:</span>
                <span className="stat-value">{lastUpdated.toLocaleTimeString()}</span>
              </div>
            )}
          </div>

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
        </>
      )}

      {/* Portfolio Companies Tab */}
      {activeTab === 'portfolio' && (
        <div className="coming-soon-section">
          <div className="coming-soon-card">
            <h2>💼 Portfolio Companies Tracker</h2>
            <p>Track your portfolio's public companies in one place</p>
            <ul className="feature-list">
              <li>• Monitor portfolio company stock prices</li>
              <li>• Performance tracking and analytics</li>
              <li>• Custom alerts and notifications</li>
              <li>• Portfolio valuation insights</li>
            </ul>
            <div className="status-badge">Coming Soon</div>
          </div>
        </div>
      )}

      {/* IPO Listings Tab */}
      {activeTab === 'ipo' && (
        <>
          <div className="ipo-tracker-header">
            <h2>🚀 Upcoming IPO Listings</h2>
            <p>Track upcoming HKEX 18A biotech IPOs and listing dates</p>
          </div>

          {upcomingIPOs && upcomingIPOs.length > 0 ? (
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
          ) : (
            <div className="no-ipos-message">
              <p>No upcoming IPOs at this time</p>
              <p className="sub-message">Check back later for new listings</p>
            </div>
          )}
        </>
      )}

      <footer className="tracker-footer">
        <p>
          Data provided by Tushare Pro API. Updates cached for 5 minutes.
        </p>
        <p className="disclaimer">
          Disclaimer: This is for informational purposes only. Not financial advice.
        </p>
      </footer>
    </div>
  );
}

export default StockTracker;
