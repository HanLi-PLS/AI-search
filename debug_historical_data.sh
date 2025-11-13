#!/bin/bash

# Debugging script for historical data display issues
# Run this on your EC2 instance

echo "========================================"
echo "Historical Data Debugging Script"
echo "========================================"
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Check if backend is running
echo -e "${YELLOW}Step 1: Checking backend status...${NC}"
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend is running${NC}"
else
    echo -e "${RED}✗ Backend is not responding${NC}"
    echo "Please start backend: pm2 restart ai-search-backend"
    exit 1
fi
echo ""

# Step 2: Check database file exists
echo -e "${YELLOW}Step 2: Checking database file...${NC}"
if [ -f "/opt/ai-search/data/db/stocks.db" ]; then
    echo -e "${GREEN}✓ Database file exists${NC}"
    ls -lh /opt/ai-search/data/db/stocks.db
else
    echo -e "${RED}✗ Database file not found${NC}"
    echo "Database should be at: /opt/ai-search/data/db/stocks.db"
fi
echo ""

# Step 3: Check database stats endpoint
echo -e "${YELLOW}Step 3: Checking database stats endpoint...${NC}"
STATS_RESPONSE=$(curl -s http://localhost:8000/api/stocks/history/stats 2>&1)
echo "Response from /api/stocks/history/stats:"
echo "$STATS_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$STATS_RESPONSE"
echo ""

TOTAL_RECORDS=$(echo "$STATS_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('total_records', 0))" 2>/dev/null)
echo "Total records in database: $TOTAL_RECORDS"
echo ""

# Step 4: Test single stock history endpoint
echo -e "${YELLOW}Step 4: Testing single stock history endpoint...${NC}"
HISTORY_RESPONSE=$(curl -s "http://localhost:8000/api/stocks/1801.HK/history?days=30" 2>&1)
echo "Response from /api/stocks/1801.HK/history:"
echo "$HISTORY_RESPONSE" | python3 -m json.tool 2>/dev/null | head -40 || echo "$HISTORY_RESPONSE"
echo ""

# Step 5: Check if data exists for 1801.HK
COUNT=$(echo "$HISTORY_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('count', 0))" 2>/dev/null)
if [ "$COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ Found $COUNT days of data for 1801.HK${NC}"
else
    echo -e "${RED}✗ No data found for 1801.HK${NC}"
    echo "Running bulk update to populate database..."
    curl -X POST http://localhost:8000/api/stocks/bulk-update-history
    echo ""
fi
echo ""

# Step 6: Check frontend is built
echo -e "${YELLOW}Step 6: Checking frontend build...${NC}"
if [ -d "/opt/ai-search/frontend/dist" ]; then
    echo -e "${GREEN}✓ Frontend dist directory exists${NC}"

    # Check if api.js is in the build
    if find /opt/ai-search/frontend/dist -name "*.js" -exec grep -l "getHistory" {} \; | head -1 > /dev/null; then
        echo -e "${GREEN}✓ getHistory function found in frontend build${NC}"
    else
        echo -e "${RED}✗ getHistory function not found in build${NC}"
        echo "Frontend needs to be rebuilt!"
        echo "Run: cd /opt/ai-search/frontend && npm run build"
    fi
else
    echo -e "${RED}✗ Frontend dist directory not found${NC}"
    echo "Please build frontend: cd /opt/ai-search/frontend && npm run build"
fi
echo ""

# Step 7: Check browser console errors
echo -e "${YELLOW}Step 7: Common issues and solutions${NC}"
echo ""
echo "If data still doesn't show in frontend:"
echo "1. Open browser DevTools (F12)"
echo "2. Go to Console tab"
echo "3. Look for errors like:"
echo "   - 404 errors on /api/stocks/*/history"
echo "   - CORS errors"
echo "   - JSON parse errors"
echo ""
echo "4. Go to Network tab"
echo "5. Click on a stock to view details"
echo "6. Check the request to /api/stocks/*/history"
echo "   - Status should be 200"
echo "   - Response should have 'data' array"
echo ""

# Step 8: Show exact curl command for testing
echo -e "${YELLOW}Step 8: Manual test command${NC}"
echo "Test the API directly with:"
echo ""
echo "curl \"http://localhost:8000/api/stocks/1801.HK/history?days=30\" | python3 -m json.tool"
echo ""

# Step 9: Check backend logs for errors
echo -e "${YELLOW}Step 9: Recent backend logs${NC}"
echo "Checking pm2 logs for errors..."
pm2 logs ai-search-backend --lines 50 --nostream 2>/dev/null | grep -E "ERROR|Exception|Traceback" | tail -20 || echo "No errors found in recent logs"
echo ""

echo -e "${GREEN}========================================"
echo "Debugging complete!"
echo "==========================================${NC}"
echo ""
echo "Summary:"
echo "- Backend running: $(curl -s http://localhost:8000/health > /dev/null 2>&1 && echo 'YES' || echo 'NO')"
echo "- Database exists: $([ -f /opt/ai-search/data/db/stocks.db ] && echo 'YES' || echo 'NO')"
echo "- Records in DB: $TOTAL_RECORDS"
echo "- 1801.HK data: $COUNT days"
echo ""
echo "If everything shows OK but frontend still doesn't work:"
echo "1. Hard refresh browser: Ctrl+Shift+R (or Cmd+Shift+R on Mac)"
echo "2. Clear browser cache and localStorage"
echo "3. Rebuild frontend: cd /opt/ai-search/frontend && npm run build && pm2 restart ai-search-frontend"
