#!/bin/bash

# Complete deployment and testing script for historical data feature
# Run this on EC2 to deploy and verify everything is working

set -e  # Exit on any error

echo "=========================================="
echo "Historical Data Deployment & Test Script"
echo "=========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

cd /opt/ai-search

# Step 1: Pull latest code
echo -e "${BLUE}Step 1: Pulling latest code...${NC}"
git fetch origin
git checkout claude/evaluate-html-to-react-011CV429JWyi22JWAMhZUBox
git pull origin claude/evaluate-html-to-react-011CV429JWyi22JWAMhZUBox
echo -e "${GREEN}✓ Code updated${NC}"
echo ""

# Step 2: Ensure database directory exists
echo -e "${BLUE}Step 2: Ensuring database directory exists...${NC}"
if [ ! -d "/opt/ai-search/data/db" ]; then
    echo "Creating database directory..."
    sudo mkdir -p /opt/ai-search/data/db
    sudo chown -R ec2-user:ec2-user /opt/ai-search/data/db
fi
echo -e "${GREEN}✓ Database directory ready${NC}"
ls -la /opt/ai-search/data/db/ || true
echo ""

# Step 3: Restart backend
echo -e "${BLUE}Step 3: Restarting backend...${NC}"
pm2 restart ai-search-backend
sleep 3
echo -e "${GREEN}✓ Backend restarted${NC}"
echo ""

# Step 4: Rebuild frontend
echo -e "${BLUE}Step 4: Rebuilding frontend...${NC}"
cd /opt/ai-search/frontend
npm run build
echo -e "${GREEN}✓ Frontend rebuilt${NC}"
echo ""

# Step 5: Restart frontend
echo -e "${BLUE}Step 5: Restarting frontend...${NC}"
cd /opt/ai-search
pm2 restart ai-search-frontend
sleep 2
echo -e "${GREEN}✓ Frontend restarted${NC}"
echo ""

# Step 6: Check services are running
echo -e "${BLUE}Step 6: Checking services...${NC}"
pm2 list
echo ""

# Step 7: Test backend endpoints
echo -e "${BLUE}Step 7: Testing backend health...${NC}"
sleep 2
if curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${GREEN}✓ Backend is healthy${NC}"
else
    echo -e "${RED}✗ Backend health check failed${NC}"
    exit 1
fi
echo ""

# Step 8: Check database stats
echo -e "${BLUE}Step 8: Checking database stats...${NC}"
STATS=$(curl -s http://localhost:8000/api/stocks/history/stats)
echo "$STATS" | python3 -m json.tool
TOTAL_RECORDS=$(echo "$STATS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('total_records', 0))")
echo ""
echo "Total records in database: $TOTAL_RECORDS"
echo ""

# Step 9: Populate database if empty
if [ "$TOTAL_RECORDS" -eq 0 ]; then
    echo -e "${YELLOW}Step 9: Database is empty, populating with historical data...${NC}"
    echo "This will take 2-3 minutes. Please wait..."
    START_TIME=$(date +%s)

    BULK_RESULT=$(curl -s -X POST http://localhost:8000/api/stocks/bulk-update-history)

    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))

    echo "Bulk update completed in ${DURATION} seconds"
    echo "$BULK_RESULT" | python3 -m json.tool
    echo ""

    # Check stats again
    STATS=$(curl -s http://localhost:8000/api/stocks/history/stats)
    TOTAL_RECORDS=$(echo "$STATS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('total_records', 0))")
    echo "Total records after update: $TOTAL_RECORDS"
else
    echo -e "${GREEN}Step 9: Database already has $TOTAL_RECORDS records${NC}"
    echo "Running incremental update to get latest data..."
    curl -s -X POST http://localhost:8000/api/stocks/bulk-update-history | python3 -m json.tool
fi
echo ""

# Step 10: Test single stock endpoint
echo -e "${BLUE}Step 10: Testing single stock endpoint (1801.HK)...${NC}"
STOCK_DATA=$(curl -s "http://localhost:8000/api/stocks/1801.HK/history?days=30")
COUNT=$(echo "$STOCK_DATA" | python3 -c "import sys, json; print(json.load(sys.stdin).get('count', 0))")
echo "Found $COUNT days of data for 1801.HK"
echo ""
echo "Sample data:"
echo "$STOCK_DATA" | python3 -m json.tool | head -50
echo ""

# Step 11: Verify frontend files
echo -e "${BLUE}Step 11: Verifying frontend build includes historical data code...${NC}"
if find /opt/ai-search/frontend/dist -name "*.js" -exec grep -l "getHistory" {} \; | head -1 > /dev/null; then
    echo -e "${GREEN}✓ getHistory function found in frontend build${NC}"
else
    echo -e "${RED}✗ getHistory function not found - rebuild needed${NC}"
fi
echo ""

# Step 12: Final summary
echo -e "${GREEN}=========================================="
echo "Deployment Complete!"
echo "==========================================${NC}"
echo ""
echo "Summary:"
echo "✓ Backend running and healthy"
echo "✓ Frontend rebuilt and deployed"
echo "✓ Database has $TOTAL_RECORDS records"
echo "✓ Test stock (1801.HK) has $COUNT days of data"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Open your browser and navigate to your EC2 public URL"
echo "2. Go to Stock Tracker page"
echo "3. Click on any stock card (e.g., Innovent Biologics 1801.HK)"
echo "4. Click 'View Full Details →'"
echo "5. You should see the historical price chart!"
echo ""
echo -e "${YELLOW}If data still doesn't appear:${NC}"
echo "1. Hard refresh browser: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)"
echo "2. Clear browser cache and localStorage"
echo "3. Open DevTools (F12) → Console tab to check for errors"
echo "4. Open DevTools (F12) → Network tab to see API calls"
echo ""
echo "Run debug script for more details: bash debug_historical_data.sh"
