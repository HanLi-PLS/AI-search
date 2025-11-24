import { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine, Label } from 'recharts';
import { stockAPI } from '../services/api';
import './StockDetail.css';

function StockDetail() {
  const { ticker } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const [stockData, setStockData] = useState(null);
  const [historyData, setHistoryData] = useState([]);
  const [returnsData, setReturnsData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [timeRange, setTimeRange] = useState('1M'); // 1W, 1M, 3M, 6M, 1Y
  const [newsExpanded, setNewsExpanded] = useState(true); // Expanded by default
  const [newsAnalysis, setNewsAnalysis] = useState(null);
  const [newsLoading, setNewsLoading] = useState(true);

  // Reset news state when ticker changes (but not when timeRange changes)
  useEffect(() => {
    setNewsAnalysis(null);
    setNewsLoading(true);
  }, [ticker]);

  useEffect(() => {
    fetchStockDetails();
  }, [ticker, timeRange]);

  // Only auto-fetch news analysis for big movers (>=10% change)
  // For others, user must click "Check Latest News" button
  useEffect(() => {
    if (stockData && ticker) {
      const dailyChange = Math.abs(stockData.change_percent || 0);
      const intradayChange = Math.abs(stockData.intraday_change_percent || 0);
      const isBigMover = dailyChange >= 10 || intradayChange >= 10;

      if (isBigMover) {
        console.log(`[StockDetail] Big mover detected (${Math.max(dailyChange, intradayChange).toFixed(2)}%), auto-fetching news analysis`);
        fetchNewsAnalysis();
      } else {
        console.log(`[StockDetail] Not a big mover (${Math.max(dailyChange, intradayChange).toFixed(2)}%), skipping auto news fetch`);
        setNewsLoading(false); // Stop loading spinner
      }
    }
  }, [stockData?.ticker]); // Only trigger when we have new stock data

  const fetchStockDetails = async () => {
    try {
      setLoading(true);
      setError(null);

      console.log(`[StockDetail] Fetching data for ${ticker}, timeRange: ${timeRange}`);

      // Fetch current price
      const priceData = await stockAPI.getPrice(ticker);
      setStockData(priceData);
      console.log('[StockDetail] Price data:', priceData);

      // Fetch historical data
      console.log(`[StockDetail] Calling getHistory(${ticker}, ${timeRange})`);
      const history = await stockAPI.getHistory(ticker, timeRange);
      console.log('[StockDetail] History data received:', {
        count: history?.length || 0,
        sample: history?.[0],
      });
      setHistoryData(history);

      if (!history || history.length === 0) {
        console.warn('[StockDetail] No historical data returned from API');
      }

      // Fetch returns data
      try {
        const returns = await stockAPI.getReturns(ticker);
        setReturnsData(returns);
        console.log('[StockDetail] Returns data:', returns);
      } catch (err) {
        console.warn('[StockDetail] Could not fetch returns:', err);
      }
    } catch (err) {
      setError('Failed to fetch stock details. Please try again.');
      console.error('[StockDetail] Error fetching stock details:', err);
      console.error('[StockDetail] Error details:', {
        message: err.message,
        response: err.response?.data,
        status: err.response?.status,
      });
    } finally {
      setLoading(false);
    }
  };

  const fetchNewsAnalysis = async (forceRefresh = false, generalNews = false) => {
    try {
      setNewsLoading(true);
      if (forceRefresh || generalNews) {
        // Don't clear existing analysis when force refreshing, just show loading
      } else {
        setNewsAnalysis(null);
      }

      console.log(`[StockDetail] Fetching news analysis for ${ticker}`, { forceRefresh, generalNews });

      // Fetch news analysis from separate endpoint
      const response = await stockAPI.getNewsAnalysis(ticker, forceRefresh, generalNews);

      if (response.news_analysis) {
        setNewsAnalysis(response.news_analysis);
        console.log('[StockDetail] News analysis loaded:', response.news_analysis);
      } else {
        console.log('[StockDetail] No news analysis available for this stock');
        setNewsAnalysis(null);
      }
    } catch (err) {
      console.warn('[StockDetail] Could not fetch news analysis:', err);
      // Don't show error to user - news analysis is optional
    } finally {
      setNewsLoading(false);
    }
  };

  // Handler for refreshing analysis (force bypass cache)
  const handleRefreshAnalysis = () => {
    if (newsAnalysis && newsAnalysis.type === 'general_news') {
      // For general news, fetch new general news
      fetchNewsAnalysis(false, true);
    } else {
      // For big mover analysis, force refresh with same prompt
      fetchNewsAnalysis(true, false);
    }
  };

  // Handler for checking general news (for non-big movers)
  const handleCheckGeneralNews = () => {
    fetchNewsAnalysis(false, true);
  };

  // Helper function to render analysis text with clickable links
  const renderAnalysisWithLinks = (text) => {
    if (!text) return null;

    // URL regex pattern that matches http://, https://, and www. URLs
    const urlPattern = /(https?:\/\/[^\s]+)|(www\.[^\s]+)/g;

    // Split text by URLs
    const parts = [];
    let lastIndex = 0;
    let match;

    while ((match = urlPattern.exec(text)) !== null) {
      // Add text before URL
      if (match.index > lastIndex) {
        parts.push({
          type: 'text',
          content: text.substring(lastIndex, match.index)
        });
      }

      // Add URL
      let url = match[0];
      // Ensure URL has protocol
      if (!url.startsWith('http')) {
        url = 'https://' + url;
      }

      parts.push({
        type: 'link',
        content: match[0],
        url: url
      });

      lastIndex = match.index + match[0].length;
    }

    // Add remaining text
    if (lastIndex < text.length) {
      parts.push({
        type: 'text',
        content: text.substring(lastIndex)
      });
    }

    // If no URLs found, return plain text
    if (parts.length === 0) {
      return <p>{text}</p>;
    }

    // Render parts with links
    return (
      <p>
        {parts.map((part, index) => {
          if (part.type === 'link') {
            return (
              <a
                key={index}
                href={part.url}
                target="_blank"
                rel="noopener noreferrer"
                className="analysis-link"
              >
                {part.content}
              </a>
            );
          }
          return <span key={index}>{part.content}</span>;
        })}
      </p>
    );
  };

  const formatPrice = (price) => {
    const currency = stockData?.currency || 'HKD';
    return `${currency} ${price ? price.toFixed(2) : 'N/A'}`;
  };

  const formatPercent = (percent) => {
    if (!percent && percent !== 0) return 'N/A';
    const sign = percent >= 0 ? '+' : '';
    return `${sign}${percent.toFixed(2)}%`;
  };

  const getChangeClass = (value) => {
    if (!value && value !== 0) return '';
    return value >= 0 ? 'positive' : 'negative';
  };

  // Handle back navigation with preserved sort parameter
  const handleBackToTracker = () => {
    const returnSort = location.state?.returnSort;
    if (returnSort) {
      navigate(`/stock-tracker?sort=${returnSort}`);
    } else {
      navigate('/stock-tracker');
    }
  };

  if (loading) {
    return (
      <div className="stock-detail-container">
        <div className="loading-container">
          <div className="spinner"></div>
          <p>Loading stock details...</p>
        </div>
      </div>
    );
  }

  if (error || !stockData) {
    return (
      <div className="stock-detail-container">
        <div className="error-container">
          <p className="error-message">{error || 'Stock not found'}</p>
          <button onClick={handleBackToTracker} className="back-button">
            ← Back to Stock Tracker
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="stock-detail-container">
      <header className="detail-header">
        <button className="back-button" onClick={handleBackToTracker}>
          ← Back to Stock Tracker
        </button>
      </header>

      <div className="stock-info-card">
        <div className="stock-header">
          <div>
            <h1>{stockData.name}</h1>
            <p className="ticker-label">{stockData.ticker}</p>
          </div>
          <div className="current-price">
            <div className="price-large">{formatPrice(stockData.current_price)}</div>

            {/* Daily Change (Today vs Yesterday) */}
            <div className="change-container">
              <span className="change-label-detail">Daily:</span>
              <div className={`change ${getChangeClass(stockData.change_percent)}`}>
                {formatPercent(stockData.change_percent)} ({formatPrice(stockData.change)})
              </div>
            </div>

            {/* Intraday Change (Close vs Open) */}
            {stockData.intraday_change !== null && stockData.intraday_change !== undefined && (
              <div className="change-container">
                <span className="change-label-detail">Intraday:</span>
                <div className={`change ${getChangeClass(stockData.intraday_change_percent)}`}>
                  {formatPercent(stockData.intraday_change_percent)} ({formatPrice(stockData.intraday_change)})
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="stock-stats">
          <div className="stat-item">
            <span className="stat-label">Previous Close</span>
            <span className="stat-value">{formatPrice(stockData.previous_close)}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Open</span>
            <span className="stat-value">{formatPrice(stockData.open)}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Day High</span>
            <span className="stat-value">{formatPrice(stockData.day_high)}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Day Low</span>
            <span className="stat-value">{formatPrice(stockData.day_low)}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Volume</span>
            <span className="stat-value">{stockData.volume?.toLocaleString() || 'N/A'}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Market Cap</span>
            <span className="stat-value">
              {stockData.market_cap ? `${stockData.market_cap.toFixed(2)} mn` : 'N/A'}
            </span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Revenue (LTM)</span>
            <span className="stat-value">
              {stockData.ttm_revenue ? `${stockData.ttm_revenue.toFixed(2)} mn` : 'N/A'}
            </span>
          </div>
          <div className="stat-item">
            <span className="stat-label">P/S Ratio</span>
            <span className="stat-value">
              {stockData.ps_ratio ? stockData.ps_ratio.toFixed(2) : 'N/A'}
            </span>
          </div>
        </div>

        {stockData.data_source && (
          <div className="data-source-badge">
            Data source: {stockData.data_source}
          </div>
        )}
      </div>

      {/* AI News Analysis Section */}
      <div className="news-analysis-section">
        <div className="news-header-detail" onClick={() => !newsLoading && newsAnalysis && setNewsExpanded(!newsExpanded)}>
          <div className="news-title-row">
            <span className="news-icon">📰</span>
            <h2>AI Market Analysis</h2>
            {newsAnalysis && newsAnalysis.type !== 'general_news' && (
              <span className="big-mover-badge-detail">🔥 Big Mover</span>
            )}
          </div>
          {!newsLoading && newsAnalysis && (
            <button className="expand-button" aria-label={newsExpanded ? "Collapse" : "Expand"}>
              {newsExpanded ? '−' : '+'}
            </button>
          )}
        </div>
        {newsLoading ? (
          <div className="news-loading">
            <div className="spinner"></div>
            <p>Analyzing market data and news...</p>
          </div>
        ) : newsAnalysis ? (
          <>
            {newsExpanded && (
              <div className="news-content-detail">
                {renderAnalysisWithLinks(newsAnalysis.analysis)}
                <div className="news-meta">
                  <span className="news-timestamp">
                    Updated: {new Date(newsAnalysis.timestamp).toLocaleString()}
                  </span>
                  <button className="refresh-analysis-button" onClick={handleRefreshAnalysis}>
                    🔄 Refresh Analysis
                  </button>
                </div>
              </div>
            )}
            {/* Always show "Check Latest News" button below the analysis if it's general news */}
            {!newsExpanded && newsAnalysis.type === 'general_news' && (
              <div className="news-collapsed-action">
                <button className="check-news-button-small" onClick={handleCheckGeneralNews}>
                  🔄 Refresh Latest News
                </button>
              </div>
            )}
          </>
        ) : (
          <div className="news-no-analysis">
            <p>No AI analysis available yet. Click below to check for latest news.</p>
            <button className="check-news-button" onClick={handleCheckGeneralNews}>
              📰 Check Latest News (Past Week)
            </button>
          </div>
        )}
      </div>

      {/* Returns Section */}
      {returnsData && returnsData.returns && (
        <div className="returns-section">
          <h2>Performance Returns</h2>
          <div className="returns-grid">
            {Object.entries(returnsData.returns).map(([period, data]) => (
              <div key={period} className="return-item">
                <div className="return-period">{data.since_listed ? 'Since Listed' : period}</div>
                <div className={`return-value ${data.return !== null && data.return >= 0 ? 'positive' : 'negative'}`}>
                  {data.return !== null ? `${data.return >= 0 ? '+' : ''}${data.return}%` : 'N/A'}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="chart-section">
        <div className="chart-header">
          <h2>Price History</h2>
          <div className="time-range-selector">
            {['1W', '1M', '3M', '6M', '1Y'].map((range) => (
              <button
                key={range}
                className={`range-button ${timeRange === range ? 'active' : ''}`}
                onClick={() => setTimeRange(range)}
              >
                {range}
              </button>
            ))}
          </div>
        </div>

        {historyData && historyData.length > 0 ? (
          <ResponsiveContainer width="100%" height={400}>
            <LineChart
              data={historyData.map(d => ({
                ...d,
                timestamp: new Date(d.date).getTime()
              }))}
              margin={{ top: 5, right: 80, left: 20, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="timestamp"
                type="number"
                scale="time"
                domain={['dataMin', 'dataMax']}
                tick={{ fontSize: 11 }}
                tickFormatter={(timestamp) => {
                  const date = new Date(timestamp);
                  const month = date.toLocaleDateString('en-US', { month: 'short' });
                  const day = date.getDate();
                  return `${month} ${day}`;
                }}
                minTickGap={50}
                angle={0}
              />
              <YAxis
                yAxisId="left"
                tick={{ fontSize: 12 }}
                domain={['auto', 'auto']}
                tickFormatter={(value) => `$${value.toFixed(2)}`}
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                tick={false}
                axisLine={false}
              />
              <Tooltip
                formatter={(value) => [`$${value.toFixed(2)}`, 'Price']}
                labelFormatter={(timestamp) => {
                  const date = new Date(timestamp);
                  return date.toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                    weekday: 'short'
                  });
                }}
              />
              <Legend />

              {/* Reference line showing latest close price */}
              <ReferenceLine
                yAxisId="left"
                y={historyData[historyData.length - 1].close}
                stroke="#2563eb"
                strokeDasharray="5 5"
                strokeWidth={1.5}
              >
                <Label
                  value={`$${historyData[historyData.length - 1].close.toFixed(2)}`}
                  position="right"
                  fill="#2563eb"
                  fontSize={14}
                  fontWeight="bold"
                  offset={10}
                />
              </ReferenceLine>

              <Line
                yAxisId="left"
                type="monotone"
                dataKey="close"
                stroke="#2563eb"
                strokeWidth={2}
                dot={false}
                name="Close Price"
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="no-chart-data">
            <p>No historical data available for this time range</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default StockDetail;
