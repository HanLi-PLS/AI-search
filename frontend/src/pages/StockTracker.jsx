import { useState, useEffect, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { stockAPI, watchlistAPI } from '../services/api';
import StockCard from '../components/StockCard';
import './StockTracker.css';

function StockTracker() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  // Initialize activeTab from URL params
  const [activeTab, setActiveTab] = useState(searchParams.get('tab') || 'hkex'); // 'hkex', 'portfolio', 'ipo', 'watchlist'

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
  const [isUpdatingPortfolioHistory, setIsUpdatingPortfolioHistory] = useState(false);

  // Watchlist state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchMarket, setSearchMarket] = useState('US');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState(null);
  const [watchlist, setWatchlist] = useState([]);
  const [watchlistLoading, setWatchlistLoading] = useState(false);
  const [watchlistError, setWatchlistError] = useState(null);
  const [watchlistRefreshing, setWatchlistRefreshing] = useState(false);
  const [addingTicker, setAddingTicker] = useState(null);
  const [removingTicker, setRemovingTicker] = useState(null);

  useEffect(() => {
    // Fetch data on initial load
    // Data is cached on server for 12 hours, so this won't cause excessive API calls
    fetchStockData();
    fetchUpcomingIPOs();
    fetchHistoryStats();
    fetchPortfolioCompanies();

    // Fetch watchlist if on watchlist tab
    if (activeTab === 'watchlist') {
      fetchWatchlist();
    }
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

          // Strip out onclick attributes from the HTML to prevent conflicts
          // The original HTML has onclick="sortTable(...)" which references a function that doesn't exist
          let cleanedHtml = response.html_content;
          if (cleanedHtml) {
            cleanedHtml = cleanedHtml.replace(/\s+onclick="[^"]*"/gi, '');
            cleanedHtml = cleanedHtml.replace(/\s+onclick='[^']*'/gi, '');
            console.log('[IPO] Removed onclick attributes from HTML');

            // Remove CSS rules that add arrow indicators via ::after pseudo-elements
            // These create duplicate arrows since we add our own
            cleanedHtml = cleanedHtml.replace(/th\.sortable::after\s*\{[^}]*\}/gi, '');
            cleanedHtml = cleanedHtml.replace(/th\.sort-asc::after\s*\{[^}]*\}/gi, '');
            cleanedHtml = cleanedHtml.replace(/th\.sort-desc::after\s*\{[^}]*\}/gi, '');
            console.log('[IPO] Removed duplicate arrow CSS rules from HTML');
          }

          setIpoHtmlContent(cleanedHtml);
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

  const handleUpdatePortfolioHistory = async () => {
    try {
      setIsUpdatingPortfolioHistory(true);

      // Update history for each portfolio company
      const tickers = portfolioCompanies.map(c => c.ticker);
      let totalRecords = 0;

      for (const ticker of tickers) {
        try {
          const result = await stockAPI.updateStockHistory(ticker);
          totalRecords += result.new_records || 0;
          console.log(`Updated ${ticker}: ${result.new_records || 0} new records`);
        } catch (err) {
          console.error(`Error updating history for ${ticker}:`, err);
        }
      }

      // Refresh stats after update
      await fetchHistoryStats();

      alert(`Successfully updated portfolio history with ${totalRecords} new records!`);
    } catch (err) {
      console.error('Error updating portfolio historical data:', err);
      alert('Failed to update portfolio historical data. Please try again.');
    } finally {
      setIsUpdatingPortfolioHistory(false);
    }
  };

  // Watchlist functions
  const fetchWatchlist = async () => {
    try {
      const hasData = watchlist.length > 0;

      if (!hasData) {
        setWatchlistLoading(true);
      } else {
        setWatchlistRefreshing(true);
      }

      setWatchlistError(null);

      const response = await watchlistAPI.getWatchlist();

      if (response.success) {
        setWatchlist(response.companies || []);
      } else {
        setWatchlistError('Failed to load watchlist');
      }
    } catch (err) {
      console.error('Error fetching watchlist:', err);
      setWatchlistError('Failed to load watchlist. Please try again.');
    } finally {
      setWatchlistLoading(false);
      setWatchlistRefreshing(false);
    }
  };

  const handleWatchlistSearch = async (e) => {
    e.preventDefault();

    if (!searchQuery.trim()) {
      setSearchError('Please enter a company name or ticker');
      return;
    }

    try {
      setSearching(true);
      setSearchError(null);
      setSearchResults([]);

      const response = await watchlistAPI.searchCompanies(
        searchQuery,
        searchMarket,
        10
      );

      if (response.success) {
        setSearchResults(response.companies || []);
        if (response.companies.length === 0) {
          setSearchError(`No companies found for "${searchQuery}" in ${searchMarket} market`);
        }
      } else {
        setSearchError('Search failed. Please try again.');
      }
    } catch (err) {
      console.error('Search error:', err);
      setSearchError('Search failed. Please check your connection.');
    } finally {
      setSearching(false);
    }
  };

  const handleAddToWatchlist = async (company) => {
    try {
      setAddingTicker(company.ticker);

      const response = await watchlistAPI.addToWatchlist(
        company.ticker,
        searchMarket
      );

      if (response.success) {
        await fetchWatchlist();
        setSearchResults(prev =>
          prev.filter(c => c.ticker !== company.ticker)
        );
        alert(`Added ${company.companyname} to watchlist!`);
      } else {
        alert(response.message || 'Failed to add to watchlist');
      }
    } catch (err) {
      console.error('Error adding to watchlist:', err);
      alert(err.response?.data?.detail || 'Failed to add to watchlist');
    } finally {
      setAddingTicker(null);
    }
  };

  const handleRemoveFromWatchlist = async (company) => {
    if (!confirm(`Remove ${company.company_name} from watchlist?`)) {
      return;
    }

    try {
      setRemovingTicker(company.ticker);

      const response = await watchlistAPI.removeFromWatchlist(
        company.ticker,
        company.market
      );

      if (response.success) {
        setWatchlist(prev =>
          prev.filter(c =>
            !(c.ticker === company.ticker && c.market === company.market)
          )
        );
        alert(`Removed ${company.company_name} from watchlist`);
      } else {
        alert('Failed to remove from watchlist');
      }
    } catch (err) {
      console.error('Error removing from watchlist:', err);
      alert('Failed to remove from watchlist');
    } finally {
      setRemovingTicker(null);
    }
  };

  // Handle tab change and persist to URL
  const handleTabChange = (tab) => {
    setActiveTab(tab);
    setSearchParams({ tab });

    // Fetch watchlist when switching to watchlist tab
    if (tab === 'watchlist' && watchlist.length === 0) {
      fetchWatchlist();
    }
  };

  // Handle sort change and persist to URL
  const handleSortChange = (newSortValue) => {
    setSortBy(newSortValue);
    const params = { sort: newSortValue };
    if (searchParams.get('tab')) {
      params.tab = searchParams.get('tab');
    }
    setSearchParams(params);
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

  // Watchlist helper functions
  const formatNumber = (value, decimals = 2) => {
    if (value === null || value === undefined) return '-';
    return Number(value).toLocaleString(undefined, {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    });
  };

  const formatLargeNumber = (value) => {
    if (value === null || value === undefined) return '-';
    if (value >= 1000000) {
      return `${(value / 1000000).toFixed(2)}T`;  // Trillions
    }
    if (value >= 1000) {
      return `${(value / 1000).toFixed(2)}B`;  // Billions
    }
    return formatNumber(value, 2);
  };

  const formatDate = (dateString) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString();
  };

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
          onClick={() => handleTabChange('hkex')}
        >
          📊 HKEX 18A Biotech
        </button>
        <button
          className={`tab-button ${activeTab === 'portfolio' ? 'active' : ''}`}
          onClick={() => handleTabChange('portfolio')}
        >
          💼 Portfolio Companies
        </button>
        <button
          className={`tab-button ${activeTab === 'ipo' ? 'active' : ''}`}
          onClick={() => handleTabChange('ipo')}
        >
          🚀 IPO Listings
        </button>
        <button
          className={`tab-button ${activeTab === 'watchlist' ? 'active' : ''}`}
          onClick={() => handleTabChange('watchlist')}
        >
          💰 Watchlist
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

              <button
                onClick={handleUpdatePortfolioHistory}
                className="refresh-button"
                disabled={isUpdatingPortfolioHistory || portfolioCompanies.length === 0}
                title="Update historical data for portfolio companies"
              >
                {isUpdatingPortfolioHistory ? '📊 Updating History...' : '📊 Update History'}
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

              // Create a ref callback to attach sorting after DOM is rendered
              const attachSortingHandlers = (containerElement) => {
                if (!containerElement) return;

                console.log('[IPO Sorting] Container element ready, attaching handlers');

                // Small delay to ensure innerHTML is processed
                setTimeout(() => {
                  const tables = containerElement.querySelectorAll('table');
                  console.log(`[IPO Sorting] Found ${tables.length} table(s) in container`);

                  tables.forEach((table, tableIndex) => {
                    const thead = table.querySelector('thead');
                    if (!thead) {
                      console.log(`[IPO Sorting] Table ${tableIndex} has no thead, skipping`);
                      return;
                    }

                    const headers = thead.querySelectorAll('th');
                    console.log(`[IPO Sorting] Table ${tableIndex} has ${headers.length} headers`);

                    headers.forEach((header, columnIndex) => {
                      // Remove any existing onclick attributes
                      header.removeAttribute('onclick');

                      // Make header sortable
                      header.style.cursor = 'pointer';
                      header.style.userSelect = 'none';
                      header.classList.add('sortable');

                      // Add sort indicator if not already present
                      if (!header.querySelector('.sort-indicator')) {
                        const indicator = document.createElement('span');
                        indicator.className = 'sort-indicator';
                        indicator.textContent = ' ↕';
                        indicator.style.opacity = '0.5';
                        header.appendChild(indicator);
                      }

                      // Add click event for sorting
                      header.onclick = function(e) {
                        e.preventDefault();
                        e.stopPropagation();
                        console.log(`[IPO Sorting] Clicked header ${columnIndex} in table ${tableIndex}`);

                        const tbody = table.querySelector('tbody');
                        if (!tbody) {
                          console.log('[IPO Sorting] No tbody found');
                          return;
                        }

                        const rows = Array.from(tbody.querySelectorAll('tr'));
                        console.log(`[IPO Sorting] Found ${rows.length} rows to sort`);

                        // Determine sort direction
                        const currentDirection = header.getAttribute('data-sort-direction');
                        const isAscending = currentDirection !== 'asc';

                        // Clear all sort indicators in this table
                        headers.forEach(th => {
                          th.removeAttribute('data-sort-direction');
                          const ind = th.querySelector('.sort-indicator');
                          if (ind) {
                            ind.textContent = ' ↕';
                            ind.style.opacity = '0.5';
                          }
                        });

                        // Update current header's sort indicator
                        const indicator = header.querySelector('.sort-indicator');
                        if (indicator) {
                          indicator.textContent = isAscending ? ' ↑' : ' ↓';
                          indicator.style.opacity = '1';
                        }
                        header.setAttribute('data-sort-direction', isAscending ? 'asc' : 'desc');

                        // Sort rows
                        rows.sort((a, b) => {
                          const aCell = a.querySelectorAll('td')[columnIndex];
                          const bCell = b.querySelectorAll('td')[columnIndex];

                          if (!aCell || !bCell) return 0;

                          const aText = aCell.textContent.trim();
                          const bText = bCell.textContent.trim();

                          // Try to parse as dates first
                          // Check if it looks like a date (contains -, /, or common date patterns)
                          const datePattern = /^\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4}|^\d{1,2}\s+\w+\s+\d{4}|\w+\s+\d{1,2},?\s+\d{4}/;
                          if (datePattern.test(aText) && datePattern.test(bText)) {
                            const aDate = new Date(aText);
                            const bDate = new Date(bText);
                            if (!isNaN(aDate.getTime()) && !isNaN(bDate.getTime())) {
                              return isAscending ? aDate - bDate : bDate - aDate;
                            }
                          }

                          // Try to parse as numbers
                          const aNum = parseFloat(aText.replace(/[,%]/g, ''));
                          const bNum = parseFloat(bText.replace(/[,%]/g, ''));

                          if (!isNaN(aNum) && !isNaN(bNum)) {
                            return isAscending ? aNum - bNum : bNum - aNum;
                          }

                          // Sort as strings
                          return isAscending
                            ? aText.localeCompare(bText)
                            : bText.localeCompare(aText);
                        });

                        // Re-append sorted rows
                        rows.forEach(row => tbody.appendChild(row));

                        console.log(`[IPO Sorting] Sorted column ${columnIndex} in ${isAscending ? 'ascending' : 'descending'} order`);
                      };
                    });

                    console.log(`[IPO Sorting] Successfully attached sorting to table ${tableIndex}`);
                  });
                }, 150);
              };

              return (
                <div className="ipo-html-container" ref={attachSortingHandlers}>
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

      {/* Watchlist Tab */}
      {activeTab === 'watchlist' && (
        <>
          <div className="watchlist-tab-container">
            {/* Search Section */}
            <div className="watchlist-search-section">
              <h2>🔍 Search Companies</h2>
              <form onSubmit={handleWatchlistSearch} className="watchlist-search-form">
                <div className="watchlist-search-input-group">
                  <input
                    type="text"
                    placeholder="Enter company name or ticker (e.g., Apple, AAPL, Tencent, 700)"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="watchlist-search-input"
                  />
                  <select
                    value={searchMarket}
                    onChange={(e) => setSearchMarket(e.target.value)}
                    className="watchlist-market-select"
                  >
                    <option value="US">🇺🇸 US Market</option>
                    <option value="HK">🇭🇰 HK Market</option>
                  </select>
                  <button
                    type="submit"
                    className="watchlist-search-button"
                    disabled={searching}
                  >
                    {searching ? 'Searching...' : 'Search'}
                  </button>
                </div>
              </form>

              {searchError && (
                <div className="watchlist-search-error">{searchError}</div>
              )}

              {searchResults.length > 0 && (
                <div className="watchlist-search-results">
                  <h3>Search Results ({searchResults.length})</h3>
                  <div className="watchlist-results-grid">
                    {searchResults.map((company) => (
                      <div key={`${company.companyid}-${company.exchange_symbol}`} className="watchlist-result-card">
                        <div className="watchlist-result-header">
                          <h4>{company.companyname}</h4>
                          <span className="watchlist-result-ticker">{company.ticker}</span>
                        </div>
                        <div className="watchlist-result-details">
                          <div className="watchlist-result-info">
                            <span className="watchlist-info-label">Exchange:</span>
                            <span className="watchlist-info-value">{company.exchange_name}</span>
                          </div>
                          {company.industry && (
                            <div className="watchlist-result-info">
                              <span className="watchlist-info-label">Industry:</span>
                              <span className="watchlist-info-value">{company.industry}</span>
                            </div>
                          )}
                          {company.webpage && (
                            <div className="watchlist-result-info">
                              <span className="watchlist-info-label">Website:</span>
                              <a
                                href={`https://${company.webpage}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="watchlist-info-link"
                              >
                                {company.webpage}
                              </a>
                            </div>
                          )}
                        </div>
                        <button
                          onClick={() => handleAddToWatchlist(company)}
                          className="watchlist-add-button"
                          disabled={addingTicker === company.ticker}
                        >
                          {addingTicker === company.ticker ? 'Adding...' : '+ Add to Watchlist'}
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Watchlist Display Section */}
            <div className="watchlist-display-section">
              <div className="watchlist-section-header">
                <h2>💼 My Watchlist ({watchlist.length})</h2>
                <button
                  onClick={fetchWatchlist}
                  className="watchlist-refresh-button"
                  disabled={watchlistRefreshing}
                >
                  {watchlistRefreshing ? '🔄 Refreshing...' : '🔄 Refresh'}
                </button>
              </div>

              {watchlistLoading && watchlist.length === 0 && (
                <div className="loading-container">
                  <div className="spinner"></div>
                  <p>Loading watchlist...</p>
                </div>
              )}

              {watchlistError && (
                <div className="error-container">
                  <p className="error-message">{watchlistError}</p>
                  <button onClick={fetchWatchlist} className="retry-button">
                    Retry
                  </button>
                </div>
              )}

              {!watchlistLoading && !watchlistError && watchlist.length === 0 && (
                <div className="watchlist-empty-watchlist">
                  <p>📭 Your watchlist is empty</p>
                  <p className="sub-message">Search for companies above to add them to your watchlist</p>
                </div>
              )}

              {!watchlistLoading && !watchlistError && watchlist.length > 0 && (
                <div className="watchlist-grid">
                  {watchlist.map((company) => (
                    <div key={company.id} className="watchlist-item-card">
                      <div className="watchlist-card-header">
                        <div>
                          <h3>{company.company_name}</h3>
                          <div className="watchlist-card-meta">
                            <span className="watchlist-ticker">{company.ticker}</span>
                            <span className="watchlist-market-badge">{company.market}</span>
                            <span className="watchlist-exchange">{company.exchange_symbol}</span>
                          </div>
                        </div>
                        <button
                          onClick={() => handleRemoveFromWatchlist(company)}
                          className="watchlist-remove-button"
                          disabled={removingTicker === company.ticker}
                          title="Remove from watchlist"
                        >
                          {removingTicker === company.ticker ? '...' : '×'}
                        </button>
                      </div>

                      {company.live_data && company.data_available ? (
                        <div className="watchlist-card-data">
                          <div className="watchlist-data-row">
                            <span className="watchlist-data-label">Price:</span>
                            <span className="watchlist-data-value watchlist-price">
                              ${formatNumber(company.live_data.price_close)}
                            </span>
                          </div>
                          <div className="watchlist-data-row">
                            <span className="watchlist-data-label">Volume:</span>
                            <span className="watchlist-data-value">
                              {formatNumber(company.live_data.volume, 0)}
                            </span>
                          </div>
                          <div className="watchlist-data-row">
                            <span className="watchlist-data-label">Market Cap:</span>
                            <span className="watchlist-data-value">
                              ${formatLargeNumber(company.live_data.market_cap)}
                            </span>
                          </div>
                          <div className="watchlist-data-row">
                            <span className="watchlist-data-label">Date:</span>
                            <span className="watchlist-data-value">
                              {formatDate(company.live_data.pricing_date)}
                            </span>
                          </div>
                        </div>
                      ) : (
                        <div className="watchlist-card-data">
                          <p className="watchlist-no-data">Live data unavailable</p>
                        </div>
                      )}

                      <div className="watchlist-card-footer">
                        {company.industry && (
                          <span className="watchlist-industry-tag">{company.industry}</span>
                        )}
                        {company.webpage && (
                          <a
                            href={`https://${company.webpage}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="watchlist-website-link"
                          >
                            🌐 Website
                          </a>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      )}

      <footer className="tracker-footer">
        <p>
          {activeTab === 'ipo'
            ? 'Data provided by Felix screening.'
            : activeTab === 'watchlist'
            ? 'Data provided by S&P Global Capital IQ via Snowflake'
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
