# Frontend Historical Data Viewing Guide

## Overview

The frontend now displays historical stock data from the database. Here's how to view and use it.

## How to View Historical Data

### Method 1: Stock Detail Page with Charts

1. **Navigate to Stock Tracker**
   - Go to `/stock-tracker` or click "Stock Tracker" from the home page

2. **Click on any stock card**
   - Click the "View Full Details →" button on any stock card
   - You'll be taken to `/stock-tracker/{ticker}` (e.g., `/stock-tracker/1801.HK`)

3. **View the Historical Chart**
   - The page displays a line chart showing price history
   - Uses Recharts library for interactive visualization
   - Hover over the chart to see exact values

4. **Change Time Range**
   - Click time range buttons at top of chart: **1W**, **1M**, **3M**, **6M**, **1Y**
   - Chart automatically updates with the selected range
   - Data is fetched from the local database (fast!)

### Method 2: Main Tracker Page

1. **View Database Statistics**
   - On the main tracker page, look at the stats bar
   - Shows "Historical Data: X records" when data is available
   - Indicates how many historical records are stored

2. **Update Historical Data**
   - Click the "📊 Update History" button
   - This triggers a bulk update for all 66 stocks
   - Fetches only new trading days since last update
   - Shows alert when complete with statistics

## Features

### Interactive Charts
- **Line chart** showing closing prices over time
- **Hover tooltips** with exact date and price
- **Responsive design** adapts to screen size
- **Auto-scaling Y-axis** for optimal view

### Time Ranges Supported
- **1W** - Last 7 days
- **1M** - Last 30 days (default)
- **3M** - Last 90 days
- **6M** - Last 180 days
- **1Y** - Last 365 days

### Data Displayed in Charts
- **Close Price** (main line in blue)
- **Date** (X-axis)
- **High/Low** (available in data, can be added to chart)
- **Volume** (available in data, can be added to chart)

## Current Implementation

### Stock Detail Page (`StockDetail.jsx`)

**What it shows:**
- Company name and ticker
- Current price and change %
- Price statistics (Open, High, Low, Previous Close, Volume, Market Cap)
- **Historical price chart** with time range selector
- Data source badge

**How it works:**
```javascript
// 1. Fetches historical data when page loads or time range changes
const history = await stockAPI.getHistory(ticker, timeRange);

// 2. API transforms database data to chart format
{
  date: "2025-11-12",
  close: 87.15,
  open: 86.0,
  high: 89.0,
  low: 84.75,
  volume: 8616404.0
}

// 3. Recharts displays the data
<LineChart data={historyData}>
  <Line dataKey="close" stroke="#2563eb" />
</LineChart>
```

### Main Tracker Page (`StockTracker.jsx`)

**New features added:**
- Shows total historical records in stats bar
- "Update History" button to trigger bulk updates
- Displays feedback when updates complete

## Testing the Historical Data Display

### On Local Development:

1. **Start the backend** (if not running):
```bash
cd /home/user/AI-search
python3 -m backend.app.main
```

2. **Start the frontend** (if not running):
```bash
cd frontend
npm run dev
```

3. **Populate the database** (first time only):
```bash
# Trigger bulk update via API
curl -X POST http://localhost:8000/api/stocks/bulk-update-history
```

4. **View in browser**:
   - Go to `http://localhost:5173/stock-tracker`
   - Click on any stock (e.g., "Innovent Biologics")
   - See the historical chart with data!

### On EC2 Production:

1. **Deploy latest code**:
```bash
cd /opt/ai-search
git pull origin claude/evaluate-html-to-react-011CV429JWyi22JWAMhZUBox
pm2 restart ai-search-backend
pm2 restart ai-search-frontend
```

2. **Populate database** (if not done):
```bash
bash /opt/ai-search/verify_historical_data.sh
```

3. **Access the app**:
   - Go to your EC2 public URL
   - Navigate to Stock Tracker
   - Click on any stock to see charts

## Example: Viewing 1801.HK Historical Data

1. **Navigate to Stock Tracker**
2. **Find "Innovent Biologics (1801.HK)"** in the list
3. **Click "View Full Details →"**
4. **You'll see:**
   - Current price: HKD 87.15
   - Change: +1.90 (+2.23%)
   - **Line chart** showing last 30 days of prices
5. **Click "3M" button** to see 90 days of history
6. **Hover over the chart** to see exact values for each day

## API Endpoints Used by Frontend

### Get Historical Data
```javascript
GET /api/stocks/{ticker}/history?days=30

Response:
{
  "ticker": "1801.HK",
  "count": 21,
  "data": [
    {
      "trade_date": "2025-11-12",
      "close": 87.15,
      "open": 86.0,
      "high": 89.0,
      "low": 84.75,
      "volume": 8616404.0
    }
  ]
}
```

### Update Single Stock
```javascript
POST /api/stocks/{ticker}/update-history

Response:
{
  "status": "success",
  "new_records": 5
}
```

### Bulk Update All Stocks
```javascript
POST /api/stocks/bulk-update-history

Response:
{
  "status": "success",
  "statistics": {
    "total": 66,
    "updated": 65,
    "new_records": 1234
  }
}
```

### Get Database Stats
```javascript
GET /api/stocks/history/stats

Response:
{
  "total_records": 5940,
  "unique_stocks": 66,
  "date_range": {
    "earliest": "2025-08-15",
    "latest": "2025-11-13"
  }
}
```

## Troubleshooting

### "No historical data available for this time range"

**Cause:** Database doesn't have data for this stock yet

**Solution:**
1. Click "Update History" on main tracker page
2. Or trigger via API: `curl -X POST http://localhost:8000/api/stocks/bulk-update-history`

### Chart is not loading

**Check:**
1. Backend is running: `curl http://localhost:8000/health`
2. Database has data: `curl http://localhost:8000/api/stocks/history/stats`
3. Browser console for errors: Press F12, check Console tab

### Chart shows old data

**Solution:**
- Click "Update History" button to fetch latest trading days
- Or use API: `curl -X POST http://localhost:8000/api/stocks/{ticker}/update-history`

## Future Enhancements (Optional)

### Additional Chart Features (can be added):
- **Volume bars** below price chart
- **Candlestick chart** instead of line chart
- **Multiple indicators** (MA, RSI, MACD)
- **Compare multiple stocks** on same chart
- **Export chart as image**

### Additional Data (already in database):
- High/Low prices (can add to chart)
- Volume (can add as bar chart)
- Change % (can add as color indicator)

## File Structure

```
frontend/
├── src/
│   ├── pages/
│   │   ├── StockTracker.jsx       # Main tracker page with stats
│   │   └── StockDetail.jsx        # Detail page with charts
│   ├── components/
│   │   └── StockCard.jsx          # Individual stock cards
│   └── services/
│       └── api.js                 # API service layer (updated)
```

## Summary

✅ **Historical data is now visible** in the frontend via interactive charts
✅ **Time ranges supported**: 1W, 1M, 3M, 6M, 1Y
✅ **Data source**: Local database (fast, no repeated API calls)
✅ **Auto-fetch**: Missing data automatically fetched from Tushare
✅ **Manual updates**: "Update History" button for on-demand updates
✅ **Stats display**: Shows how many records are in database

The complete end-to-end system is now working!
