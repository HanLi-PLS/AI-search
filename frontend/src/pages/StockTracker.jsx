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
  const [ipoColumns, setIpoColumns] = useState([]);
  const [ipoMetadata, setIpoMetadata] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [historyStats, setHistoryStats] = useState(null);
  const [isUpdatingHistory, setIsUpdatingHistory] = useState(false);

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
    fetchHistoryStats();
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
      const response = await stockAPI.getUpcomingIPOs();
      console.log('[IPO] Response:', response);

      if (response.success && response.data) {
        setUpcomingIPOs(response.data);
        setIpoColumns(response.columns || []);
        setIpoMetadata({
          count: response.count,
          source: response.source,
          last_updated: response.last_updated
        });
      } else {
        console.error('[IPO] Failed to load IPO data:', response.error);
        setUpcomingIPOs([]);
      }
    } catch (err) {
      console.error('Error fetching upcoming IPOs:', err);
      setUpcomingIPOs([]);
    }
  };

  const fetchHistoryStats = async () => {
    try {
      const stats = await stockAPI.getHistoryStats();
      setHistoryStats(stats);
    } catch (err) {
      console.error('Error fetching history stats:', err);
    }
  };

  const handleBulkUpdateHistory = async () => {
    try {
      setIsUpdatingHistory(true);
      const result = await stockAPI.bulkUpdateHistory();
      console.log('Bulk update result:', result);

      // Refresh stats after update
      await fetchHistoryStats();

      alert(`Successfully updated ${result.statistics.updated} stocks with ${result.statistics.new_records} new records!`);
    } catch (err) {
      console.error('Error updating historical data:', err);
      alert('Failed to update historical data. Please try again.');
    } finally {
      setIsUpdatingHistory(false);
    }
  };

  // Helper function to render cell values with clickable links
  const renderCellValue = (value, columnName) => {
    if (value === null || value === undefined) {
      return <span className="empty-cell">-</span>;
    }

    // Convert value to string for checking
    const strValue = String(value);

    // Check if value looks like a URL
    const urlPattern = /^(https?:\/\/|www\.)/i;
    const isUrl = urlPattern.test(strValue);

    if (isUrl) {
      // Ensure URL has protocol
      const fullUrl = strValue.startsWith('http') ? strValue : `https://${strValue}`;
      return (
        <a
          href={fullUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="table-link"
        >
          {strValue}
        </a>
      );
    }

    // Check if value contains a URL (e.g., "See: https://example.com")
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    const urls = strValue.match(urlRegex);

    if (urls && urls.length > 0) {
      // Split text and URLs
      const parts = strValue.split(urlRegex);
      return (
        <span>
          {parts.map((part, index) => {
            if (urls.includes(part)) {
              return (
                <a
                  key={index}
                  href={part}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="table-link"
                >
                  {part}
                </a>
              );
            }
            return <span key={index}>{part}</span>;
          })}
        </span>
      );
    }

    // Regular value - format if it's a number or date
    if (typeof value === 'number') {
      // Check if it looks like a date (year > 1900)
      if (value > 19000000 && value < 21000000) {
        // Might be a date in YYYYMMDD format
        const dateStr = strValue;
        if (dateStr.length === 8) {
          const year = dateStr.substring(0, 4);
          const month = dateStr.substring(4, 6);
          const day = dateStr.substring(6, 8);
          return `${year}-${month}-${day}`;
        }
      }
      return value.toLocaleString();
    }

    // Check if it's an ISO date string
    if (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}T/.test(value)) {
      return new Date(value).toLocaleString();
    }

    return strValue;
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

            <button
              onClick={handleBulkUpdateHistory}
              className="refresh-button"
              disabled={isUpdatingHistory}
              title="Update historical data for all stocks"
            >
              {isUpdatingHistory ? '📊 Updating History...' : '📊 Update History'}
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
            {historyStats && historyStats.total_records > 0 && (
              <div className="stat">
                <span className="stat-label">Historical Data:</span>
                <span className="stat-value" title={`${historyStats.total_records} records in database`}>
                  {historyStats.total_records.toLocaleString()} records
                </span>
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
            <h2>🚀 HKEX IPO Tracker</h2>
            <p>Public company tracker for HKEX listings</p>
            {ipoMetadata && (
              <div className="ipo-metadata">
                <span className="metadata-item">
                  📊 {ipoMetadata.count} companies tracked
                </span>
                {ipoMetadata.last_updated && (
                  <span className="metadata-item">
                    🕒 Updated: {new Date(ipoMetadata.last_updated).toLocaleString()}
                  </span>
                )}
              </div>
            )}
          </div>

          {upcomingIPOs && upcomingIPOs.length > 0 ? (
            <div className="ipo-table-container">
              <table className="ipo-table">
                <thead>
                  <tr>
                    {ipoColumns.map((col, index) => (
                      <th key={index}>{col}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {upcomingIPOs.map((row, rowIndex) => (
                    <tr key={rowIndex}>
                      {ipoColumns.map((col, colIndex) => (
                        <td key={colIndex}>
                          {renderCellValue(row[col], col)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="no-ipos-message">
              <p>Loading IPO data...</p>
              <p className="sub-message">Please wait</p>
            </div>
          )}
        </>
      )}

      <footer className="tracker-footer">
        <p>
          {activeTab === 'ipo'
            ? 'Data provided by Felix screening.'
            : 'Data provided by Tushare Pro API. Updates cached for 5 minutes.'}
        </p>
        <p className="disclaimer">
          Disclaimer: This is for informational purposes only. Not financial advice.
        </p>
      </footer>
    </div>
  );
}

export default StockTracker;
