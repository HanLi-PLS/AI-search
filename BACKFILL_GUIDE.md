# Historical Data Backfill Guide

## Problem

Currently, the database only has **3 months** of historical data. This means:
- ✅ **1W** and **1M** time ranges work correctly
- ❌ **3M**, **6M**, and **1Y** all show the same curve (only 3 months)

## Solution

Run the backfill script to fetch **1 year** of historical data for all stocks.

## Quick Start

### On EC2:

```bash
cd /opt/ai-search

# Pull latest code
git pull origin claude/evaluate-html-to-react-011CV429JWyi22JWAMhZUBox

# Restart backend to load new endpoints
pm2 restart ai-search-backend

# Wait for backend to start
sleep 5

# Run the backfill script
bash backfill_historical_data.sh
```

The script will:
1. ✅ Check backend is running
2. ✅ Show current database stats
3. ✅ Ask for confirmation
4. ✅ Backfill 365 days of data for all 66 stocks
5. ✅ Show before/after statistics
6. ✅ Report any errors

**Estimated time:** 3-5 minutes

## What Happens During Backfill

For each stock that already has data:
1. Find the **earliest date** currently in database (e.g., Aug 15, 2024)
2. Fetch data going **backwards 365 days** from that date (e.g., Aug 15, 2023)
3. Store the new historical data
4. Skip stocks with no existing data (they'll get 1 year on next update)

## After Backfill

You'll have up to **1 year** of historical data (or full trading history if the stock was listed less than 1 year ago).

### Frontend Impact:

- **1W** - Shows last 7 days
- **1M** - Shows last 30 days
- **3M** - Shows last 90 days (different from 6M and 1Y now!)
- **6M** - Shows last 180 days (different curve!)
- **1Y** - Shows last 365 days (full year!)

### Charts Handle Missing Data:

If a stock was listed less than 1 year ago:
- Chart shows only available data
- No errors or "null" values displayed
- Line starts from IPO date

## Manual Backfill (Optional)

### Backfill Single Stock:

```bash
# Backfill 1 year for stock 1801.HK
curl -X POST "http://localhost:8000/api/stocks/1801.HK/backfill-history?days=365"
```

Response:
```json
{
  "status": "success",
  "ticker": "1801.HK",
  "new_records": 245,
  "message": "Backfilled 1801.HK with 245 new records"
}
```

### Backfill All Stocks:

```bash
# Backfill 1 year for all 66 stocks
curl -X POST "http://localhost:8000/api/stocks/bulk-backfill-history?days=365"
```

Response:
```json
{
  "status": "success",
  "days_requested": 365,
  "statistics": {
    "total": 66,
    "backfilled": 65,
    "new_records": 15890,
    "errors": 0,
    "skipped": 1
  }
}
```

### Custom Days:

You can backfill any number of days:

```bash
# Backfill 2 years (730 days) for all stocks
curl -X POST "http://localhost:8000/api/stocks/bulk-backfill-history?days=730"
```

## API Endpoints

### 1. Backfill Single Stock

**Endpoint:** `POST /api/stocks/{ticker}/backfill-history`

**Parameters:**
- `ticker` (path): Stock ticker (e.g., "1801.HK")
- `days` (query, optional): Number of days to backfill (default: 365)

**Example:**
```bash
curl -X POST "http://localhost:8000/api/stocks/1801.HK/backfill-history?days=365"
```

**Response:**
```json
{
  "status": "success",
  "ticker": "1801.HK",
  "ts_code": "01801.HK",
  "days_requested": 365,
  "new_records": 245,
  "message": "Backfilled 1801.HK with 245 new records"
}
```

### 2. Bulk Backfill All Stocks

**Endpoint:** `POST /api/stocks/bulk-backfill-history`

**Parameters:**
- `days` (query, optional): Number of days to backfill per stock (default: 365)

**Example:**
```bash
curl -X POST "http://localhost:8000/api/stocks/bulk-backfill-history?days=365"
```

**Response:**
```json
{
  "status": "success",
  "days_requested": 365,
  "statistics": {
    "total": 66,
    "backfilled": 65,
    "new_records": 15890,
    "errors": 0,
    "skipped": 1
  }
}
```

**Statistics explained:**
- `total`: Total number of stocks attempted
- `backfilled`: Number of stocks successfully backfilled
- `new_records`: Total new records added to database
- `errors`: Number of stocks that had errors
- `skipped`: Stocks with no existing data (can't backfill, use update instead)

## How Backfill Works

### Backfill vs Update:

**Update (Incremental):**
- Fetches data going **forward** from latest date
- Use for daily updates: `POST /api/stocks/bulk-update-history`
- Example: Latest date is Nov 12 → fetches Nov 13, Nov 14, etc.

**Backfill:**
- Fetches data going **backward** from earliest date
- Use for getting older history: `POST /api/stocks/bulk-backfill-history`
- Example: Earliest date is Aug 15 → fetches Aug 14, Aug 13, ..., back 365 days

### Database Behavior:

- **Upsert logic**: If a record already exists (same ticker + date), it updates it
- **No duplicates**: Safe to run backfill multiple times
- **Missing dates**: Trading holidays/weekends are naturally skipped by Tushare API

## Verification

### Check Database Stats:

```bash
curl http://localhost:8000/api/stocks/history/stats | python3 -m json.tool
```

**Before backfill:**
```json
{
  "total_records": 5940,
  "unique_stocks": 66,
  "date_range": {
    "earliest": "2024-08-15",
    "latest": "2024-11-13"
  }
}
```

**After backfill (expected):**
```json
{
  "total_records": 21000,
  "unique_stocks": 66,
  "date_range": {
    "earliest": "2023-08-15",
    "latest": "2024-11-13"
  }
}
```

### Check Single Stock:

```bash
curl "http://localhost:8000/api/stocks/1801.HK/history?days=365" | python3 -m json.tool | head -30
```

Should show up to 365 days of data.

### Test in Frontend:

1. Open Stock Tracker in browser
2. Click on any stock
3. Try all time ranges:
   - **1M** - Should show ~22 trading days
   - **3M** - Should show ~65 trading days
   - **6M** - Should show ~130 trading days
   - **1Y** - Should show ~245 trading days

Each should show a **different curve** now!

## Troubleshooting

### Error: "No existing data for ticker"

**Cause:** Stock has no data in database yet.

**Fix:** Run update instead of backfill:
```bash
curl -X POST "http://localhost:8000/api/stocks/1801.HK/update-history"
```

### Error: API quota exceeded

**Cause:** Tushare API has rate limits or quota limits.

**Fix:**
- Wait and try again later
- Or upgrade your Tushare plan
- Or backfill in smaller batches (fewer days at a time)

### Some stocks show errors

**Check logs:**
```bash
pm2 logs ai-search-backend --lines 100 | grep -i error
```

Common issues:
- Stock was delisted (no historical data available)
- Stock ticker format incorrect
- Tushare API temporary issue

## Daily Maintenance

After initial backfill, you only need **incremental updates** daily:

### Set up cron job:

```bash
# Edit crontab
crontab -e

# Add this line (runs daily at 8 PM HKT)
0 20 * * * curl -X POST http://localhost:8000/api/stocks/bulk-update-history
```

This fetches only **new trading days**, not the full history again.

## Summary

- ✅ **Initial setup:** Run `bash backfill_historical_data.sh` to get 1 year of data
- ✅ **Daily updates:** Use `/api/stocks/bulk-update-history` (only new days)
- ✅ **More history:** Re-run backfill with more days if needed
- ✅ **Frontend:** All time ranges (1W, 1M, 3M, 6M, 1Y) now show different curves

The backfill is a **one-time operation** to fill in historical data. After that, daily incremental updates keep it fresh!
