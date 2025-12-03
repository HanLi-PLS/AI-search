import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { watchlistAPI } from '../services/api';
import { showSuccess, showError, showInfo } from '../utils/toast';
import { exportWatchlistToCSV } from '../utils/csvExport';
import './Watchlist.css';

function Watchlist() {
  const navigate = useNavigate();

  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchMarket, setSearchMarket] = useState('US');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState(null);

  // Watchlist state
  const [watchlist, setWatchlist] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  // UI state
  const [addingTicker, setAddingTicker] = useState(null);
  const [removingTicker, setRemovingTicker] = useState(null);

  // Load watchlist on mount
  useEffect(() => {
    fetchWatchlist();
  }, []);

  const fetchWatchlist = async () => {
    try {
      const hasData = watchlist.length > 0;

      if (!hasData) {
        setLoading(true);
      } else {
        setRefreshing(true);
      }

      setError(null);

      const response = await watchlistAPI.getWatchlist();

      if (response.success) {
        setWatchlist(response.companies || []);
      } else {
        setError('Failed to load watchlist');
      }
    } catch (err) {
      console.error('Error fetching watchlist:', err);
      setError('Failed to load watchlist. Please try again.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleSearch = async (e) => {
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
        // Refresh watchlist to show new item
        await fetchWatchlist();

        // Remove from search results
        setSearchResults(prev =>
          prev.filter(c => c.ticker !== company.ticker)
        );

        showSuccess(`Added ${company.companyname} to watchlist!`);
      } else {
        showError(response.message || 'Failed to add to watchlist');
      }
    } catch (err) {
      console.error('Error adding to watchlist:', err);
      showError(err.response?.data?.detail || 'Failed to add to watchlist');
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
        // Remove from local state
        setWatchlist(prev =>
          prev.filter(c =>
            !(c.ticker === company.ticker && c.market === company.market)
          )
        );

        showSuccess(`Removed ${company.company_name} from watchlist`);
      } else {
        showError('Failed to remove from watchlist');
      }
    } catch (err) {
      console.error('Error removing from watchlist:', err);
      showError('Failed to remove from watchlist');
    } finally {
      setRemovingTicker(null);
    }
  };

  const handleExportCSV = () => {
    if (watchlist.length === 0) {
      showInfo('No data to export. Add companies to your watchlist first.');
      return;
    }

    try {
      exportWatchlistToCSV(watchlist);
      showSuccess(`Exported ${watchlist.length} companies to CSV`);
    } catch (err) {
      console.error('Error exporting CSV:', err);
      showError('Failed to export CSV. Please try again.');
    }
  };

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
    <div className="watchlist-container">
      <header className="watchlist-header">
        <button className="back-button" onClick={() => navigate('/')}>
          ← Back to Home
        </button>
        <h1>📊 Watchlist</h1>
        <p className="header-subtitle">Track companies from US and HK markets with real-time CapIQ data</p>
      </header>

      {/* Search Section */}
      <div className="search-section">
        <h2>🔍 Search Companies</h2>
        <form onSubmit={handleSearch} className="search-form">
          <div className="search-input-group">
            <input
              type="text"
              placeholder="Enter company name or ticker (e.g., Apple, AAPL, Tencent, 700)"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="search-input"
            />
            <select
              value={searchMarket}
              onChange={(e) => setSearchMarket(e.target.value)}
              className="market-select"
            >
              <option value="US">🇺🇸 US Market</option>
              <option value="HK">🇭🇰 HK Market</option>
            </select>
            <button
              type="submit"
              className="search-button"
              disabled={searching}
            >
              {searching ? 'Searching...' : 'Search'}
            </button>
          </div>
        </form>

        {searchError && (
          <div className="search-error">{searchError}</div>
        )}

        {searchResults.length > 0 && (
          <div className="search-results">
            <h3>Search Results ({searchResults.length})</h3>
            <div className="results-grid">
              {searchResults.map((company) => (
                <div key={`${company.companyid}-${company.exchange_symbol}`} className="result-card">
                  <div className="result-header">
                    <h4>{company.companyname}</h4>
                    <span className="result-ticker">{company.ticker}</span>
                  </div>
                  <div className="result-details">
                    <div className="result-info">
                      <span className="info-label">Exchange:</span>
                      <span className="info-value">{company.exchange_name}</span>
                    </div>
                    {company.industry && (
                      <div className="result-info">
                        <span className="info-label">Industry:</span>
                        <span className="info-value">{company.industry}</span>
                      </div>
                    )}
                    {company.webpage && (
                      <div className="result-info">
                        <span className="info-label">Website:</span>
                        <a
                          href={`https://${company.webpage}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="info-link"
                        >
                          {company.webpage}
                        </a>
                      </div>
                    )}
                  </div>
                  <button
                    onClick={() => handleAddToWatchlist(company)}
                    className="add-button"
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

      {/* Watchlist Section */}
      <div className="watchlist-section">
        <div className="section-header">
          <h2>💼 My Watchlist ({watchlist.length})</h2>
          <div className="header-actions">
            <button
              onClick={handleExportCSV}
              className="export-button"
              disabled={watchlist.length === 0}
              title="Export to CSV"
            >
              📥 Export CSV
            </button>
            <button
              onClick={fetchWatchlist}
              className="refresh-button"
              disabled={refreshing}
            >
              {refreshing ? '🔄 Refreshing...' : '🔄 Refresh'}
            </button>
          </div>
        </div>

        {loading && watchlist.length === 0 && (
          <div className="loading-container">
            <div className="spinner"></div>
            <p>Loading watchlist...</p>
          </div>
        )}

        {error && (
          <div className="error-container">
            <p className="error-message">{error}</p>
            <button onClick={fetchWatchlist} className="retry-button">
              Retry
            </button>
          </div>
        )}

        {!loading && !error && watchlist.length === 0 && (
          <div className="empty-watchlist">
            <p>📭 Your watchlist is empty</p>
            <p className="sub-message">Search for companies above to add them to your watchlist</p>
          </div>
        )}

        {!loading && !error && watchlist.length > 0 && (
          <div className="watchlist-grid">
            {watchlist.map((company) => (
              <div key={company.id} className="watchlist-card">
                <div className="card-header">
                  <div>
                    <h3>{company.company_name}</h3>
                    <div className="card-meta">
                      <span className="ticker">{company.ticker}</span>
                      <span className="market-badge">{company.market}</span>
                      <span className="exchange">{company.exchange_symbol}</span>
                    </div>
                  </div>
                  <button
                    onClick={() => handleRemoveFromWatchlist(company)}
                    className="remove-button"
                    disabled={removingTicker === company.ticker}
                    title="Remove from watchlist"
                  >
                    {removingTicker === company.ticker ? '...' : '×'}
                  </button>
                </div>

                {company.live_data && company.data_available ? (
                  <div className="card-data">
                    <div className="data-row">
                      <span className="data-label">Price:</span>
                      <span className="data-value price">
                        ${formatNumber(company.live_data.price_close)}
                      </span>
                    </div>
                    <div className="data-row">
                      <span className="data-label">Volume:</span>
                      <span className="data-value">
                        {formatNumber(company.live_data.volume, 0)}
                      </span>
                    </div>
                    <div className="data-row">
                      <span className="data-label">Market Cap:</span>
                      <span className="data-value">
                        ${formatLargeNumber(company.live_data.market_cap)}
                      </span>
                    </div>
                    <div className="data-row">
                      <span className="data-label">Revenue (LTM):</span>
                      <span className="data-value">
                        {company.live_data.ttm_revenue
                          ? `${formatLargeNumber(company.live_data.ttm_revenue)} ${company.live_data.ttm_revenue_currency || 'USD'}`
                          : 'N/A'}
                      </span>
                    </div>
                    {company.live_data.exchange_rate_used && (
                      <div className="data-row">
                        <span className="data-label">Exchange Rate:</span>
                        <span className="data-value">
                          1 {company.live_data.ttm_revenue_currency} = {company.live_data.exchange_rate_used.toFixed(4)} {company.live_data.market_cap_currency}
                        </span>
                      </div>
                    )}
                    <div className="data-row">
                      <span className="data-label">P/S Ratio:</span>
                      <span className="data-value">
                        {company.live_data.ps_ratio
                          ? formatNumber(company.live_data.ps_ratio, 2)
                          : 'N/A'}
                      </span>
                    </div>
                    {company.live_data.listing_date && (
                      <div className="data-row">
                        <span className="data-label">Listing Date:</span>
                        <span className="data-value">
                          {formatDate(company.live_data.listing_date)}
                        </span>
                      </div>
                    )}
                    <div className="data-row">
                      <span className="data-label">Date:</span>
                      <span className="data-value">
                        {formatDate(company.live_data.pricing_date)}
                      </span>
                    </div>
                  </div>
                ) : (
                  <div className="card-data">
                    <p className="no-data">Live data unavailable</p>
                  </div>
                )}

                <div className="card-footer">
                  {company.industry && (
                    <span className="industry-tag">{company.industry}</span>
                  )}
                  {company.webpage && (
                    <a
                      href={`https://${company.webpage}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="website-link"
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

      <footer className="watchlist-footer">
        <p>Data provided by S&P Global Capital IQ via Snowflake</p>
        <p className="disclaimer">
          Disclaimer: This is for informational purposes only. Not financial advice.
        </p>
      </footer>
    </div>
  );
}

export default Watchlist;
