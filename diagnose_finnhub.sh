#!/bin/bash

echo "=========================================="
echo "Finnhub API Diagnostic for ZBIO"
echo "=========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Step 1: Pulling latest code with debug logging...${NC}"
git pull origin claude/evaluate-html-to-react-011CV429JWyi22JWAMhZUBox
echo ""

echo -e "${YELLOW}Step 2: Restarting backend to pick up new logging...${NC}"
pm2 restart ai-search-backend
sleep 3
echo ""

echo -e "${YELLOW}Step 3: Testing Finnhub API directly...${NC}"
echo "This will test if Finnhub API key is accessible and working"
python3 test_finnhub_zbio.py
echo ""

echo -e "${YELLOW}Step 4: Triggering ZBIO historical data fetch...${NC}"
echo "Making request to: http://localhost:8000/api/stocks/ZBIO/update-history"
RESPONSE=$(curl -s -X POST http://localhost:8000/api/stocks/ZBIO/update-history)
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

echo -e "${YELLOW}Step 5: Checking backend logs for errors...${NC}"
echo "Last 30 lines of backend logs:"
pm2 logs ai-search-backend --lines 30 --nostream
echo ""

echo -e "${YELLOW}Step 6: Checking database for ZBIO records...${NC}"
RESPONSE=$(curl -s "http://localhost:8000/api/stocks/ZBIO/history?days=365")
COUNT=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('count', 0))" 2>/dev/null)

if [ "$COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ ZBIO: $COUNT historical records found${NC}"
else
    echo -e "${RED}✗ ZBIO: No historical data in database${NC}"
fi
echo ""

echo "=========================================="
echo "Diagnosis Complete"
echo "=========================================="
echo ""
echo "If you see errors about 'Finnhub API key not available':"
echo "  1. Check AWS Secrets Manager has 'finnhub-api-key' secret"
echo "  2. Check EC2 IAM role has permission to read secrets"
echo "  3. Check backend/.env has USE_AWS_SECRETS=true"
echo ""
echo "If Finnhub API works but returns no data:"
echo "  1. Check if ZBIO ticker is correct"
echo "  2. Check if Finnhub API has ZBIO data availability"
echo "  3. Check rate limits on Finnhub API"
