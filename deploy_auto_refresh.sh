#!/bin/bash

echo "=========================================="
echo "Auto-Refresh Feature Deployment"
echo "=========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Step 1: Installing APScheduler dependency...${NC}"
pip3 install APScheduler>=3.10.0 || echo -e "${RED}Warning: pip installation failed${NC}"

# Install in backend virtualenv if it exists
if [ -d "/opt/ai-search/backend/venv" ]; then
    echo "Installing in backend virtualenv..."
    /opt/ai-search/backend/venv/bin/pip install APScheduler>=3.10.0 || echo -e "${RED}Warning: venv installation failed${NC}"
elif [ -d "backend/venv" ]; then
    echo "Installing in backend virtualenv (relative path)..."
    backend/venv/bin/pip install APScheduler>=3.10.0 || echo -e "${RED}Warning: venv installation failed${NC}"
fi
echo ""

echo -e "${YELLOW}Step 2: Pulling latest code...${NC}"
git pull origin claude/evaluate-html-to-react-011CV429JWyi22JWAMhZUBox
echo ""

echo -e "${YELLOW}Step 3: Restarting backend with scheduler...${NC}"
pm2 restart ai-search-backend
sleep 5
echo ""

echo -e "${YELLOW}Step 4: Checking scheduler status...${NC}"
echo "Checking backend logs for scheduler confirmation..."
pm2 logs ai-search-backend --lines 20 --nostream | grep -i "scheduler\|refresh" || echo "Scheduler logs not found yet, give it a few moments"
echo ""

echo -e "${YELLOW}Step 5: Rebuilding frontend...${NC}"
cd frontend
npm run build
cd ..
echo ""

echo -e "${YELLOW}Step 6: Restarting frontend...${NC}"
pm2 restart ai-search-frontend
sleep 3
echo ""

echo -e "${YELLOW}Step 7: Testing force refresh functionality...${NC}"
echo "Testing HKEX 18A force refresh..."
RESPONSE=$(curl -s "http://localhost:8000/api/stocks/prices?force_refresh=true" | head -c 200)
if echo "$RESPONSE" | grep -q "ticker"; then
    echo -e "${GREEN}✓ HKEX 18A force refresh working${NC}"
else
    echo -e "${RED}✗ HKEX 18A force refresh failed${NC}"
fi

echo ""
echo "Testing Portfolio force refresh..."
RESPONSE=$(curl -s "http://localhost:8000/api/stocks/portfolio?force_refresh=true" | head -c 200)
if echo "$RESPONSE" | grep -q "success"; then
    echo -e "${GREEN}✓ Portfolio force refresh working${NC}"
else
    echo -e "${RED}✗ Portfolio force refresh failed${NC}"
fi
echo ""

echo "=========================================="
echo "Summary of Changes"
echo "=========================================="
echo ""
echo "Backend changes:"
echo "  - Added APScheduler for scheduled data refresh"
echo "  - Scheduler runs at 12 AM and 12 PM daily"
echo "  - Added force_refresh parameter to stock endpoints"
echo "  - Updated cache TTL from 5 minutes to 12 hours"
echo ""
echo "Files created:"
echo "  - backend/app/services/scheduler.py"
echo ""
echo "Files modified:"
echo "  - backend/app/main.py (start/stop scheduler)"
echo "  - backend/app/api/routes/stocks.py (force_refresh support)"
echo "  - backend/app/services/portfolio.py (caching support)"
echo "  - frontend/src/services/api.js (force_refresh parameter)"
echo "  - frontend/src/pages/StockTracker.jsx (refresh buttons)"
echo "  - requirements.txt (APScheduler added)"
echo ""
echo "Frontend changes:"
echo "  - Removed local storage caching (now uses 12-hour server cache)"
echo "  - Refresh buttons now force fresh data fetch"
echo "  - Regular page loads use cached data"
echo ""
echo "Data refresh schedule:"
echo "  ⏰ Automatic: 12:00 AM (midnight)"
echo "  ⏰ Automatic: 12:00 PM (noon)"
echo "  🔄 Manual: Click refresh button anytime"
echo ""
echo "Deployment complete!"
echo "Visit the Stock Tracker to test the refresh buttons."
echo ""
echo "To verify scheduler is running, check backend logs:"
echo "  pm2 logs ai-search-backend"
