import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { stockAPI } from '../services/api';
import './StockDetail.css';

function StockDetail() {
  const { ticker } = useParams();
  const navigate = useNavigate();
  const [stockData, setStockData] = useState(null);
  const [historyData, setHistoryData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [timeRange, setTimeRange] = useState('1M'); // 1W, 1M, 3M, 6M, 1Y

  useEffect(() => {
    fetchStockDetails();
  }, [ticker, timeRange]);

  const fetchStockDetails = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch current price
      const priceData = await stockAPI.getPrice(ticker);
      setStockData(priceData);

      // Fetch historical data
      const history = await stockAPI.getHistory(ticker, timeRange);
      setHistoryData(history);
    } catch (err) {
      setError('Failed to fetch stock details. Please try again.');
      console.error('Error fetching stock details:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatPrice = (price) => {
    return `HKD ${price ? price.toFixed(2) : 'N/A'}`;
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
          <button onClick={() => navigate('/stock-tracker')} className="back-button">
            ← Back to Stock Tracker
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="stock-detail-container">
      <header className="detail-header">
        <button className="back-button" onClick={() => navigate('/stock-tracker')}>
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
            <div className={`change ${getChangeClass(stockData.change_percent)}`}>
              {formatPercent(stockData.change_percent)} ({formatPrice(stockData.change)})
            </div>
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
            <span className="stat-value">{formatPrice(stockData.high)}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Day Low</span>
            <span className="stat-value">{formatPrice(stockData.low)}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Volume</span>
            <span className="stat-value">{stockData.volume?.toLocaleString() || 'N/A'}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Market Cap</span>
            <span className="stat-value">{stockData.market_cap || 'N/A'}</span>
          </div>
        </div>

        {stockData.data_source && (
          <div className="data-source-badge">
            Data source: {stockData.data_source}
          </div>
        )}
      </div>

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
            <LineChart data={historyData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 12 }}
                tickFormatter={(date) => new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
              />
              <YAxis
                tick={{ fontSize: 12 }}
                domain={['auto', 'auto']}
                tickFormatter={(value) => `$${value.toFixed(2)}`}
              />
              <Tooltip
                formatter={(value) => [`$${value.toFixed(2)}`, 'Price']}
                labelFormatter={(date) => new Date(date).toLocaleDateString('en-US', {
                  year: 'numeric',
                  month: 'short',
                  day: 'numeric'
                })}
              />
              <Legend />
              <Line
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
