# Quick Start: Fix Historical Data Display

If historical data is not showing in your frontend, follow these steps on your **EC2 instance**:

## 🚀 One-Command Deploy & Test

Run this single command to deploy everything and test it:

```bash
cd /opt/ai-search && bash deploy_and_test_historical_data.sh
```

This script will:
- Pull latest code
- Rebuild frontend
- Restart backend and frontend
- Test all endpoints
- Populate database if needed
- Show you the results

**Estimated time:** 3-5 minutes

## 🔍 If Still Not Working

### Step 1: Run Debug Script

```bash
cd /opt/ai-search && bash debug_historical_data.sh
```

This will check:
- Backend status
- Database existence and records count
- API endpoints functionality
- Frontend build status

### Step 2: Check Browser Console

1. Open your app in browser
2. Press **F12** to open DevTools
3. Go to **Console** tab
4. Click on a stock to view details
5. Look for these debug messages:

```
[API] getHistory called: ticker=1801.HK, timeRange=1M, days=30
[API] Requesting: /api/stocks/1801.HK/history?days=30
[API] Raw response: {...}
[API] Transformed 21 records for chart
[StockDetail] History data received: {count: 21, sample: {...}}
```

### Step 3: Check Network Tab

1. In DevTools, go to **Network** tab
2. Click on a stock to view details
3. Look for request to `/api/stocks/.../history`
4. Check:
   - **Status:** Should be `200 OK`
   - **Response:** Should have `data` array with stock records

## 🐛 Common Issues & Fixes

### Issue 1: "No historical data available for this time range"

**Cause:** Database is empty

**Fix:**
```bash
curl -X POST http://localhost:8000/api/stocks/bulk-update-history
```

### Issue 2: 404 Error on `/api/stocks/.../history`

**Cause:** Backend not deployed or outdated

**Fix:**
```bash
cd /opt/ai-search
git pull origin claude/evaluate-html-to-react-011CV429JWyi22JWAMhZUBox
pm2 restart ai-search-backend
```

### Issue 3: Old code still running

**Cause:** Frontend not rebuilt

**Fix:**
```bash
cd /opt/ai-search/frontend
npm run build
pm2 restart ai-search-frontend
```

### Issue 4: Browser cache

**Cause:** Old JavaScript cached

**Fix:**
- Hard refresh: **Ctrl+Shift+R** (Windows) or **Cmd+Shift+R** (Mac)
- Or clear browser cache completely

## ✅ How to Verify It's Working

### Backend Test:
```bash
curl "http://localhost:8000/api/stocks/1801.HK/history?days=30" | python3 -m json.tool | head -50
```

**Expected:** JSON with `count` and `data` array containing stock records

### Frontend Test:
1. Go to your EC2 public URL
2. Navigate to **Stock Tracker**
3. Click on any stock card (e.g., "Innovent Biologics")
4. Click **"View Full Details →"**
5. You should see:
   - A blue line chart showing price history
   - Time range buttons: 1W | 1M | 3M | 6M | 1Y
   - Clickable time ranges update the chart

### Console Test:
Open browser console (F12) and you should see logs like:
```
[API] getHistory called: ticker=1801.HK, timeRange=1M, days=30
[API] Transformed 21 records for chart
[StockDetail] History data received: {count: 21, sample: {...}}
```

## 📊 What Should You See

When working correctly, the Stock Detail page shows:

1. **Top Section:**
   - Company name and ticker
   - Current price and change %
   - Stock statistics (Open, High, Low, Volume, etc.)

2. **Chart Section:**
   - Heading: "Price History"
   - Time range buttons: **1W | 1M | 3M | 6M | 1Y** (1M is active by default)
   - **Blue line chart** showing closing prices over time
   - Hover over chart to see exact values

3. **No Errors:**
   - No red error messages
   - No "No historical data available" message (unless database is truly empty)

## 💡 Quick Debug Checklist

Run these commands on EC2 and check the results:

```bash
# 1. Is backend running?
curl http://localhost:8000/health
# Expected: {"status":"healthy"}

# 2. Does database have data?
curl http://localhost:8000/api/stocks/history/stats | python3 -m json.tool
# Expected: total_records > 0

# 3. Can I get stock history?
curl "http://localhost:8000/api/stocks/1801.HK/history?days=30" | python3 -m json.tool | head -30
# Expected: JSON with count and data array

# 4. Is frontend built with new code?
find /opt/ai-search/frontend/dist -name "*.js" -exec grep -l "getHistory" {} \; | head -1
# Expected: Path to a JavaScript file
```

If all 4 checks pass, the issue is likely browser cache. Hard refresh!

## 🆘 Still Not Working?

1. **Check PM2 logs** for backend errors:
   ```bash
   pm2 logs ai-search-backend --lines 100
   ```

2. **Check if Tushare token is set**:
   ```bash
   echo $TUSHARE_API_TOKEN
   ```
   Should show your token. If empty, set it in `.env` file.

3. **Manually test one stock update**:
   ```bash
   curl -X POST "http://localhost:8000/api/stocks/1801.HK/update-history" | python3 -m json.tool
   ```
   Should return success with new_records count.

4. **Check database file permissions**:
   ```bash
   ls -la /opt/ai-search/data/db/stocks.db
   ```
   Should be owned by ec2-user or your user.

## 📞 Next Steps

If you've tried everything above and it still doesn't work:

1. Share the output of `bash debug_historical_data.sh`
2. Share browser console errors (F12 → Console tab)
3. Share network request details (F12 → Network tab → click on failing request)

This will help identify the exact issue!
