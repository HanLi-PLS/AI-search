#!/bin/bash

echo "=========================================="
echo "Backfill ZBIO Historical Data (1 Year)"
echo "=========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Step 1: Checking current ZBIO data...${NC}"
RESPONSE=$(curl -s "http://localhost:8000/api/stocks/ZBIO/history?days=365")
BEFORE_COUNT=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('count', 0))" 2>/dev/null)
echo "Current records: $BEFORE_COUNT"

if [ "$BEFORE_COUNT" -gt 0 ]; then
    FIRST_DATE=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); records = data.get('data', []); print(records[-1]['trade_date'] if records else 'N/A')" 2>/dev/null)
    LAST_DATE=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); records = data.get('data', []); print(records[0]['trade_date'] if records else 'N/A')" 2>/dev/null)
    echo "Date range: $FIRST_DATE to $LAST_DATE"
fi
echo ""

echo -e "${YELLOW}Step 2: Backfilling 365 days of historical data...${NC}"
echo "This will fetch data going backwards from the earliest date we have"
RESPONSE=$(curl -s -X POST "http://localhost:8000/api/stocks/ZBIO/backfill-history?days=365")
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"

NEW_RECORDS=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('new_records', 0))" 2>/dev/null)
echo ""
echo "New records added: $NEW_RECORDS"
echo ""

echo -e "${YELLOW}Step 3: Verifying updated data...${NC}"
RESPONSE=$(curl -s "http://localhost:8000/api/stocks/ZBIO/history?days=365")
AFTER_COUNT=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('count', 0))" 2>/dev/null)
echo "Total records now: $AFTER_COUNT"

if [ "$AFTER_COUNT" -gt "$BEFORE_COUNT" ]; then
    FIRST_DATE=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); records = data.get('data', []); print(records[-1]['trade_date'] if records else 'N/A')" 2>/dev/null)
    LAST_DATE=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); records = data.get('data', []); print(records[0]['trade_date'] if records else 'N/A')" 2>/dev/null)
    echo "New date range: $FIRST_DATE to $LAST_DATE"
    echo ""
    echo -e "${GREEN}✓ SUCCESS: ZBIO historical data backfilled${NC}"
else
    echo -e "${RED}✗ No new records added${NC}"
    echo ""
    echo "This might mean:"
    echo "  1. No older data is available from yfinance"
    echo "  2. The earliest date we have is already at yfinance's limit"
fi
echo ""

echo "=========================================="
echo "Backfill Complete"
echo "=========================================="
echo ""
echo "The stock detail page should now show a full year of historical data."
