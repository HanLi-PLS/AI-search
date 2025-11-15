#!/bin/bash

# Verification script for historical stock data system
# Run this on EC2 to test the complete implementation

echo "=========================================="
echo "Historical Stock Data System Verification"
echo "=========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Check backend health
echo -e "${YELLOW}Step 1: Checking backend health...${NC}"
if curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${GREEN}✓ Backend is running${NC}"
else
    echo -e "${RED}✗ Backend is not responding${NC}"
    echo "Please start the backend first"
    exit 1
fi
echo ""

# Step 2: Check database stats (initial state)
echo -e "${YELLOW}Step 2: Checking initial database stats...${NC}"
curl -s http://localhost:8000/api/stocks/history/stats | python3 -m json.tool | head -20
echo ""

# Step 3: Test single stock historical data
echo -e "${YELLOW}Step 3: Testing single stock historical data (1801.HK)...${NC}"
RESPONSE=$(curl -s "http://localhost:8000/api/stocks/1801.HK/history?days=30")
COUNT=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('count', 0))")
echo "Found $COUNT days of historical data for 1801.HK"
echo "$RESPONSE" | python3 -m json.tool | head -30
echo ""

# Step 4: Trigger bulk update for all stocks
echo -e "${YELLOW}Step 4: Triggering bulk update for all 66 stocks...${NC}"
echo "This may take 2-3 minutes. Please wait..."
START_TIME=$(date +%s)
BULK_RESPONSE=$(curl -s -X POST http://localhost:8000/api/stocks/bulk-update-history)
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo "Bulk update completed in ${DURATION} seconds"
echo "$BULK_RESPONSE" | python3 -m json.tool
echo ""

# Step 5: Check final database stats
echo -e "${YELLOW}Step 5: Checking final database stats...${NC}"
FINAL_STATS=$(curl -s http://localhost:8000/api/stocks/history/stats)
echo "$FINAL_STATS" | python3 -m json.tool | head -30
echo ""

# Summary
TOTAL_RECORDS=$(echo "$FINAL_STATS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('total_records', 0))")
UNIQUE_STOCKS=$(echo "$FINAL_STATS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('unique_stocks', 0))")

echo -e "${GREEN}=========================================="
echo "Verification Summary"
echo "==========================================${NC}"
echo "Total records in database: $TOTAL_RECORDS"
echo "Unique stocks tracked: $UNIQUE_STOCKS"
echo ""

if [ "$TOTAL_RECORDS" -gt 1000 ]; then
    echo -e "${GREEN}✓ Database successfully populated with historical data${NC}"
    echo -e "${GREEN}✓ System is ready for production use${NC}"
else
    echo -e "${YELLOW}⚠ Database has fewer records than expected${NC}"
    echo "Expected: ~5000-6000 records (66 stocks × ~90 days)"
    echo "Check backend logs for any API errors"
fi
echo ""

# Step 6: Test incremental update
echo -e "${YELLOW}Step 6: Testing incremental update for one stock...${NC}"
INCREMENTAL_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/stocks/1801.HK/update-history")
echo "$INCREMENTAL_RESPONSE" | python3 -m json.tool
echo ""

echo -e "${GREEN}Verification complete!${NC}"
