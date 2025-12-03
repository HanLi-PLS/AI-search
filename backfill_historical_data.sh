#!/bin/bash

# Backfill historical data to get 1 year of data for all stocks
# This script fills in the missing historical data (currently only have 3 months)

echo "=========================================="
echo "Historical Data Backfill Script"
echo "=========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if backend is running
echo -e "${BLUE}Checking backend status...${NC}"
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${RED}✗ Backend is not running${NC}"
    echo "Please start backend first: pm2 restart ai-search-backend"
    exit 1
fi
echo -e "${GREEN}✓ Backend is running${NC}"
echo ""

# Show current database stats
echo -e "${BLUE}Current database statistics:${NC}"
CURRENT_STATS=$(curl -s http://localhost:8000/api/stocks/history/stats)
echo "$CURRENT_STATS" | python3 -m json.tool | head -20
echo ""

CURRENT_RECORDS=$(echo "$CURRENT_STATS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('total_records', 0))")
echo "Current total records: $CURRENT_RECORDS"
echo ""

# Ask for confirmation
echo -e "${YELLOW}This will backfill 1 year of historical data for all 66 stocks.${NC}"
echo "This may take 3-5 minutes and will make multiple API calls to Tushare."
echo ""
read -p "Do you want to continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Backfill cancelled."
    exit 0
fi
echo ""

# Run the backfill
echo -e "${BLUE}Starting bulk backfill (365 days)...${NC}"
echo "This will fetch historical data going backwards from the earliest date we have."
echo "Please wait..."
echo ""

START_TIME=$(date +%s)
BACKFILL_RESULT=$(curl -s -X POST "http://localhost:8000/api/stocks/bulk-backfill-history?days=365")
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo -e "${GREEN}Backfill completed in ${DURATION} seconds${NC}"
echo ""
echo "Backfill results:"
echo "$BACKFILL_RESULT" | python3 -m json.tool
echo ""

# Show updated stats
echo -e "${BLUE}Updated database statistics:${NC}"
FINAL_STATS=$(curl -s http://localhost:8000/api/stocks/history/stats)
echo "$FINAL_STATS" | python3 -m json.tool | head -20
echo ""

FINAL_RECORDS=$(echo "$FINAL_STATS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('total_records', 0))")
NEW_RECORDS=$((FINAL_RECORDS - CURRENT_RECORDS))

echo -e "${GREEN}=========================================="
echo "Backfill Summary"
echo "==========================================${NC}"
echo "Records before: $CURRENT_RECORDS"
echo "Records after: $FINAL_RECORDS"
echo "New records added: $NEW_RECORDS"
echo ""

# Extract stats from backfill result
BACKFILLED=$(echo "$BACKFILL_RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('statistics', {}).get('backfilled', 0))")
ERRORS=$(echo "$BACKFILL_RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('statistics', {}).get('errors', 0))")

echo "Stocks backfilled: $BACKFILLED / 66"
echo "Errors: $ERRORS"
echo ""

if [ "$ERRORS" -gt 0 ]; then
    echo -e "${YELLOW}⚠ Some stocks had errors. Check backend logs:${NC}"
    echo "pm2 logs ai-search-backend --lines 50"
    echo ""
fi

echo -e "${GREEN}✓ Backfill complete!${NC}"
echo ""
echo "You can now view up to 1 year of historical data in the frontend."
echo "Time ranges 3M, 6M, and 1Y should now show different curves."
echo ""
echo "Test it:"
echo "1. Go to Stock Tracker in browser"
echo "2. Click on any stock"
echo "3. Try different time ranges: 1M, 3M, 6M, 1Y"
