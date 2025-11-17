import { useState, useEffect, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { stockAPI } from '../services/api';
import StockCard from '../components/StockCard';
import './StockTracker.css';

function StockTracker() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState('hkex'); // 'hkex', 'portfolio', 'ipo'
  const [stockData, setStockData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  // Initialize sortBy from URL params, default to 'name'
  const [sortBy, setSortBy] = useState(searchParams.get('sort') || 'name');
  const [upcomingIPOs, setUpcomingIPOs] = useState([]);
  const [ipoColumns, setIpoColumns] = useState([]);
  const [ipoMetadata, setIpoMetadata] = useState(null);
  const [ipoHtmlContent, setIpoHtmlContent] = useState(null);
  const [ipoFormat, setIpoFormat] = useState('table'); // 'table' or 'html'
  const [lastUpdated, setLastUpdated] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [historyStats, setHistoryStats] = useState(null);
  const [isUpdatingHistory, setIsUpdatingHistory] = useState(false);
  const [portfolioCompanies, setPortfolioCompanies] = useState([]);
  const [portfolioLoading, setPortfolioLoading] = useState(false);
  const [portfolioRefreshing, setPortfolioRefreshing] = useState(false);

  useEffect(() => {
    // Fetch data on initial load
    // Data is cached on server for 12 hours, so this won't cause excessive API calls
    fetchStockData();
    fetchUpcomingIPOs();
    fetchHistoryStats();
    fetchPortfolioCompanies();
  }, []);

  const fetchStockData = async (forceRefresh = false) => {
    try {
      const hasCachedData = stockData.length > 0;

      if (!hasCachedData) {
        setLoading(true);
      } else if (forceRefresh) {
        setIsRefreshing(true);
      }

      setError(null);

      // Pass forceRefresh to API - server caches data for 12 hours
      const data = await stockAPI.getAllPrices(forceRefresh);
      setStockData(data);
      setLastUpdated(new Date());

      console.log(forceRefresh ? 'Force refreshed stock data' : 'Loaded stock data from server cache');
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
      console.log('[IPO] Fetching IPO data...');
      const response = await stockAPI.getUpcomingIPOs();
      console.log('[IPO] Response received:', response);
      console.log('[IPO] Response format:', response.format);
      console.log('[IPO] Response success:', response.success);

      if (response.success) {
        const format = response.format || 'table';
        console.log('[IPO] Setting format to:', format);
        setIpoFormat(format);

        if (response.format === 'html') {
          // Handle HTML content
          console.log('[IPO] HTML content length:', response.html_content?.length);
          setIpoHtmlContent(response.html_content);
          setIpoMetadata({
            source: response.source,
            last_updated: response.last_updated
          });
          console.log('[IPO] HTML content set successfully');
        } else {
          // Handle table data (CSV/Excel)
          console.log('[IPO] Table data rows:', response.data?.length);
          setUpcomingIPOs(response.data || []);
          setIpoColumns(response.columns || []);
          setIpoMetadata({
            count: response.count,
            source: response.source,
            last_updated: response.last_updated
          });
          console.log('[IPO] Table data set successfully');
        }
      } else {
        console.error('[IPO] Failed to load IPO data:', response.error);
        setUpcomingIPOs([]);
        setIpoHtmlContent(null);
      }
    } catch (err) {
      console.error('Error fetching upcoming IPOs:', err);
      console.error('Error details:', err.message, err.stack);
      setUpcomingIPOs([]);
      setIpoHtmlContent(null);
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

  const fetchPortfolioCompanies = async (forceRefresh = false) => {
    try {
      const hasCachedData = portfolioCompanies.length > 0;

      if (!hasCachedData) {
        setPortfolioLoading(true);
      } else if (forceRefresh) {
        setPortfolioRefreshing(true);
      }

      // Pass forceRefresh to API - server caches data for 12 hours
      const response = await stockAPI.getPortfolioCompanies(forceRefresh);
      console.log('[Portfolio] Response:', response);

      if (response.success && response.companies) {
        setPortfolioCompanies(response.companies);
      } else {
        console.error('[Portfolio] Failed to load portfolio data');
        setPortfolioCompanies([]);
      }

      console.log(forceRefresh ? 'Force refreshed portfolio data' : 'Loaded portfolio data from server cache');
    } catch (err) {
      console.error('Error fetching portfolio companies:', err);
      setPortfolioCompanies([]);
    } finally {
      setPortfolioLoading(false);
      setPortfolioRefreshing(false);
    }
  };

  // Handle sort change and persist to URL
  const handleSortChange = (newSortValue) => {
    setSortBy(newSortValue);
    setSearchParams({ sort: newSortValue });
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
                onChange={(e) => handleSortChange(e.target.value)}
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
        <>
          <div className="tracker-header">
            <h2>💼 Portfolio Companies</h2>
            <p className="header-subtitle">Track your portfolio's public companies across markets</p>
          </div>

          <div className="controls-section">
            <div className="control-group">
              <button
                onClick={() => fetchPortfolioCompanies(true)}
                className="refresh-button"
                disabled={portfolioRefreshing}
              >
                {portfolioRefreshing ? '🔄 Refreshing...' : '🔄 Refresh'}
              </button>
            </div>

            <div className="stats-bar">
              <div className="stat">
                <span className="stat-label">Portfolio Companies:</span>
                <span className="stat-value">{portfolioCompanies.length}</span>
              </div>
              <div className="stat">
                <span className="stat-label">Markets:</span>
                <span className="stat-value">HKEX, NASDAQ</span>
              </div>
            </div>
          </div>

          {portfolioLoading && portfolioCompanies.length === 0 ? (
            <div className="loading-container">
              <div className="spinner"></div>
              <p>Loading portfolio companies...</p>
            </div>
          ) : portfolioCompanies.length > 0 ? (
            <div className="stocks-grid">
              {portfolioCompanies.map((company) => (
                <StockCard key={company.ticker} stock={company} />
              ))}
            </div>
          ) : (
            <div className="no-results">
              <p>No portfolio companies to display</p>
            </div>
          )}
        </>
      )}

      {/* IPO Listings Tab */}
      {activeTab === 'ipo' && (
        <>
          <div className="ipo-tracker-header">
            <h2>🚀 HKEX IPO Tracker</h2>
            <p>Public company tracker for HKEX listings</p>
            {ipoMetadata && (
              <div className="ipo-metadata">
                {ipoMetadata.count && (
                  <span className="metadata-item">
                    📊 {ipoMetadata.count} companies tracked
                  </span>
                )}
                {ipoMetadata.last_updated && (
                  <span className="metadata-item">
                    🕒 Updated: {new Date(ipoMetadata.last_updated).toLocaleString()}
                  </span>
                )}
              </div>
            )}
          </div>

          {(() => {
            console.log('[IPO RENDER] Format:', ipoFormat, 'HTML Content exists:', !!ipoHtmlContent, 'Table rows:', upcomingIPOs?.length);

            if (ipoFormat === 'html' && ipoHtmlContent) {
              console.log('[IPO RENDER] Showing HTML content');
              return (
                <div className="ipo-html-container">
                  <div dangerouslySetInnerHTML={{ __html: ipoHtmlContent }} />
                </div>
              );
            } else if (ipoFormat === 'table' && upcomingIPOs && upcomingIPOs.length > 0) {
              console.log('[IPO RENDER] Showing table');
              return (
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
              );
            } else {
              console.log('[IPO RENDER] Showing loading state');
              return (
                <div className="no-ipos-message">
                  <p>Loading IPO data...</p>
                  <p className="sub-message">Please wait</p>
                </div>
              );
            }
          })()}
        </>
      )}

      <footer className="tracker-footer">
        <p>
          {activeTab === 'ipo'
            ? 'Data provided by Felix screening.'
            : 'Data provided by Tushare Pro API, Finnhub, and Yahoo Finance. Auto-refreshes at 12 AM and 12 PM daily.'}
        </p>
        <p className="disclaimer">
          Disclaimer: This is for informational purposes only. Not financial advice.
        </p>
      </footer>
    </div>
  );
}

export default StockTracker;
