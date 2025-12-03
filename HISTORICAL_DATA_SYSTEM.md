# Historical Stock Data Storage System

## Overview

This system stores historical stock price data locally in a SQLite database to avoid repeated API calls to Tushare. It automatically fetches only new data daily through incremental updates.

## Architecture

### Database
- **Location**: `data/db/stocks.db` (SQLite)
- **Model**: `StockDaily` (backend/app/models/stock.py)
- **Fields**: ticker, ts_code, trade_date, OHLCV data, volume, amount, change metrics

### Service Layer
- **File**: `backend/app/services/stock_data.py`
- **Class**: `StockDataService`
- **Key Methods**:
  - `get_latest_date(ticker)` - Find the last date we have data for
  - `fetch_and_store_historical_data(ticker, ts_code, start_date, end_date)` - Fetch from Tushare and store
  - `update_incremental(ticker, ts_code)` - Fetch only new data since last update
  - `get_historical_data(ticker, start_date, end_date, limit)` - Query from database
  - `bulk_update_all_stocks(tickers)` - Update all stocks incrementally

### API Endpoints

#### 1. Get Historical Data
```bash
GET /api/stocks/{ticker}/history?days=90
```
**Parameters:**
- `days` (optional): Number of days to retrieve (default: 90)
- `start_date` (optional): Start date in YYYY-MM-DD format
- `end_date` (optional): End date in YYYY-MM-DD format

**Response:**
```json
{
  "ticker": "1801.HK",
  "start_date": "2025-10-14",
  "end_date": "2025-11-13",
  "count": 21,
  "data": [
    {
      "ticker": "1801.HK",
      "ts_code": "01801.HK",
      "trade_date": "2025-11-12",
      "open": 86.0,
      "high": 89.0,
      "low": 84.75,
      "close": 87.15,
      "pre_close": 85.25,
      "volume": 8616404.0,
      "amount": 754431530.45,
      "change": 1.9,
      "pct_change": 2.23,
      "data_source": "Tushare Pro"
    }
  ]
}
```

**Auto-fetch**: If no data exists in database, automatically fetches from Tushare.

#### 2. Update Single Stock
```bash
POST /api/stocks/{ticker}/update-history
```
Manually trigger incremental update for a specific stock.

**Response:**
```json
{
  "status": "success",
  "ticker": "1801.HK",
  "ts_code": "01801.HK",
  "new_records": 5,
  "message": "Updated 1801.HK with 5 new records"
}
```

#### 3. Bulk Update All Stocks
```bash
POST /api/stocks/bulk-update-history
```
Update all 66 HKEX 18A biotech stocks incrementally.

**Response:**
```json
{
  "status": "success",
  "statistics": {
    "total": 66,
    "updated": 65,
    "new_records": 1234,
    "errors": 1
  }
}
```

#### 4. Database Statistics
```bash
GET /api/stocks/history/stats
```
Get statistics about stored historical data.

**Response:**
```json
{
  "total_records": 5940,
  "unique_stocks": 66,
  "date_range": {
    "earliest": "2025-08-15",
    "latest": "2025-11-13"
  },
  "stocks": [
    {
      "ticker": "1801.HK",
      "ts_code": "01801.HK",
      "record_count": 90,
      "earliest_date": "2025-08-15",
      "latest_date": "2025-11-13"
    }
  ]
}
```

## Usage

### Initial Setup

1. **Database Initialization** (automatic on startup):
```python
# backend/app/main.py already includes this
from backend.app.database import init_db
init_db()
```

2. **First Time Data Load**:
```bash
# Fetch 90 days of historical data for all stocks
curl -X POST http://localhost:8000/api/stocks/bulk-update-history
```
This takes ~2-3 minutes and creates ~5000-6000 records.

### Daily Updates

Run incremental update to fetch only new trading days:

```bash
# Update all stocks (only fetches new days)
curl -X POST http://localhost:8000/api/stocks/bulk-update-history
```

Or set up a cron job:
```bash
# Add to crontab (runs daily at 8 PM HKT)
0 20 * * * curl -X POST http://localhost:8000/api/stocks/bulk-update-history
```

### Query Historical Data

```bash
# Get last 90 days for a stock
curl "http://localhost:8000/api/stocks/1801.HK/history?days=90"

# Get data for specific date range
curl "http://localhost:8000/api/stocks/1801.HK/history?start_date=2025-01-01&end_date=2025-11-13"

# Get last 30 days
curl "http://localhost:8000/api/stocks/1801.HK/history?days=30"
```

## Incremental Update Logic

```python
def update_incremental(ticker, ts_code):
    # 1. Get latest date in database for this ticker
    latest_date = get_latest_date(ticker)

    if latest_date:
        # 2. Fetch from day after latest to today
        start_date = latest_date + 1 day
    else:
        # 3. No data exists, fetch last 90 days
        start_date = today - 90 days

    end_date = today

    # 4. Fetch and store only new data
    fetch_and_store_historical_data(ticker, ts_code, start_date, end_date)
```

## Benefits

1. **Reduced API Calls**: Only fetch new data, not entire history repeatedly
2. **Fast Queries**: Database queries are instant vs. API calls
3. **Offline Access**: Historical data available even if Tushare API is down
4. **Cost Effective**: Minimizes API quota usage
5. **Automatic Updates**: Incremental updates only fetch missing days

## Database Schema

```sql
CREATE TABLE stock_daily (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker VARCHAR(20) NOT NULL,
    ts_code VARCHAR(20) NOT NULL,
    trade_date DATE NOT NULL,
    open FLOAT,
    high FLOAT,
    low FLOAT,
    close FLOAT NOT NULL,
    pre_close FLOAT,
    volume FLOAT,
    amount FLOAT,
    change FLOAT,
    pct_change FLOAT,
    data_source VARCHAR(50) DEFAULT 'Tushare Pro',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ticker, trade_date)
);

CREATE INDEX ix_ticker_trade_date ON stock_daily(ticker, trade_date);
```

## Frontend Integration

The frontend can use cached data and show historical charts without repeated API calls:

```javascript
// Fetch 90 days of historical data for a stock
const response = await fetch(`/api/stocks/${ticker}/history?days=90`);
const { data } = await response.json();

// Data is ready for charting (e.g., with Chart.js, Recharts, etc.)
const chartData = data.map(d => ({
  date: d.trade_date,
  close: d.close,
  volume: d.volume
}));
```

## Monitoring

Check database health and stats:

```bash
# Get database statistics
curl http://localhost:8000/api/stocks/history/stats | python3 -m json.tool

# Check logs for any Tushare API errors
tail -f /opt/ai-search/logs/backend.log | grep -i "tushare\|historical"
```

## Troubleshooting

### No Data Returned

Check if data exists:
```bash
curl http://localhost:8000/api/stocks/history/stats
```

If `total_records` is 0, run bulk update:
```bash
curl -X POST http://localhost:8000/api/stocks/bulk-update-history
```

### Tushare API Errors

Check backend logs:
```bash
tail -100 /opt/ai-search/logs/backend.log
```

Common issues:
- API token not configured: Set `TUSHARE_API_TOKEN` in environment
- API quota exceeded: Wait for quota reset or upgrade plan
- Network issues: Check EC2 internet connectivity

### Database Lock Errors

SQLite can have concurrent write issues. If you see database lock errors:
```bash
# Check for any stuck processes
ps aux | grep python
```

## Files Modified

- `backend/app/database.py` - Database configuration with lazy initialization
- `backend/app/models/stock.py` - StockDaily model
- `backend/app/services/stock_data.py` - StockDataService (NEW)
- `backend/app/api/routes/stocks.py` - Added historical data endpoints
- `backend/app/main.py` - Added database initialization on startup

## Git Commits

```
0311a95 Remove old placeholder /stocks/history/{ticker} endpoint
16c6396 Fix: Database permission error - use relative path and lazy initialization
0320050 Feature: Add database-backed historical stock data storage
```
