import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './StockCard.css';

function StockCard({ stock }) {
  const navigate = useNavigate();
  const [showDetails, setShowDetails] = useState(false);

  const formatNumber = (num) => {
    if (num === null || num === undefined) return 'N/A';
    return num.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  };

  const formatMarketCap = (marketCap) => {
    if (!marketCap) return 'N/A';
    if (marketCap >= 1e9) {
      return `${(marketCap / 1e9).toFixed(2)}B`;
    }
    if (marketCap >= 1e6) {
      return `${(marketCap / 1e6).toFixed(2)}M`;
    }
    return formatNumber(marketCap);
  };

  const getChangeClass = (change) => {
    if (!change) return '';
    return change >= 0 ? 'positive' : 'negative';
  };

  if (stock.error) {
    return (
      <div className="stock-card error-card">
        <div className="stock-header">
          <h3>{stock.name}</h3>
          <span className="ticker">{stock.ticker}</span>
        </div>
        <div className="error-content">
          <p>⚠️ Unable to fetch data</p>
          <p className="error-detail">{stock.error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`stock-card ${stock.news_analysis ? 'has-news' : ''}`}>
      <div className="stock-header">
        <div>
          <h3>{stock.name}</h3>
          <span className="ticker">{stock.ticker}</span>
          {stock.news_analysis && (
            <span className="big-mover-badge" title="Significant price move (≥10%)">
              🔥 Big Mover
            </span>
          )}
        </div>
        <button
          className="details-toggle"
          onClick={() => setShowDetails(!showDetails)}
        >
          {showDetails ? '−' : '+'}
        </button>
      </div>

      <div className="stock-price-section">
        <div className="current-price">
          <span className="currency">{stock.currency}</span>
          <span className="price">{formatNumber(stock.current_price)}</span>
        </div>

        {/* Daily Change (Today vs Yesterday) */}
        {stock.change !== null && stock.change !== undefined && (
          <div className="change-row">
            <span className="change-label">Daily:</span>
            <div className={`price-change ${getChangeClass(stock.change)}`}>
              <span className="change-value">
                {stock.change >= 0 ? '+' : ''}
                {formatNumber(stock.change)}
              </span>
              <span className="change-percent">
                ({stock.change_percent >= 0 ? '+' : ''}
                {formatNumber(stock.change_percent)}%)
              </span>
            </div>
          </div>
        )}

        {/* Intraday Change (Close vs Open) */}
        {stock.intraday_change !== null && stock.intraday_change !== undefined && (
          <div className="change-row">
            <span className="change-label">Intraday:</span>
            <div className={`price-change ${getChangeClass(stock.intraday_change)}`}>
              <span className="change-value">
                {stock.intraday_change >= 0 ? '+' : ''}
                {formatNumber(stock.intraday_change)}
              </span>
              <span className="change-percent">
                ({stock.intraday_change_percent >= 0 ? '+' : ''}
                {formatNumber(stock.intraday_change_percent)}%)
              </span>
            </div>
          </div>
        )}
      </div>

      {/* News Analysis for Big Movers */}
      {stock.news_analysis && (
        <div className="news-analysis">
          <div className="news-header">
            <span className="news-icon">📰</span>
            <span className="news-title">Market Analysis</span>
          </div>
          <p className="news-content">{stock.news_analysis.analysis}</p>
        </div>
      )}

      {showDetails && (
        <div className="stock-details">
          <div className="detail-row">
            <span className="detail-label">Open:</span>
            <span className="detail-value">{formatNumber(stock.open)}</span>
          </div>
          <div className="detail-row">
            <span className="detail-label">Previous Close:</span>
            <span className="detail-value">
              {formatNumber(stock.previous_close)}
            </span>
          </div>
          <div className="detail-row">
            <span className="detail-label">Day High:</span>
            <span className="detail-value">{formatNumber(stock.day_high)}</span>
          </div>
          <div className="detail-row">
            <span className="detail-label">Day Low:</span>
            <span className="detail-value">{formatNumber(stock.day_low)}</span>
          </div>
          <div className="detail-row">
            <span className="detail-label">Volume:</span>
            <span className="detail-value">
              {stock.volume ? stock.volume.toLocaleString() : 'N/A'}
            </span>
          </div>
          <div className="detail-row">
            <span className="detail-label">Market Cap:</span>
            <span className="detail-value">
              {stock.currency} {formatMarketCap(stock.market_cap)}
            </span>
          </div>
        </div>
      )}

      <div className="stock-footer">
        <span className="last-updated">
          Updated: {new Date(stock.last_updated).toLocaleTimeString()}
        </span>
        <button
          className="view-details-button"
          onClick={() => navigate(`/stock-tracker/${stock.ticker}`)}
        >
          View Full Details →
        </button>
      </div>
    </div>
  );
}

export default StockCard;
