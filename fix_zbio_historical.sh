#!/bin/bash

echo "=========================================="
echo "Fix ZBIO Historical Data - Quick Deploy"
echo "=========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Step 1: Installing finnhub-python in backend environment...${NC}"

# Check if using virtualenv
if pm2 list | grep -q "ai-search-backend"; then
    # Get the interpreter from pm2
    PYTHON_PATH=$(pm2 jlist | python3 -c "import sys, json; apps = json.load(sys.stdin); backend = [a for a in apps if a['name'] == 'ai-search-backend']; print(backend[0]['pm2_env']['exec_interpreter'] if backend else 'python3')" 2>/dev/null)

    if [ -z "$PYTHON_PATH" ]; then
        PYTHON_PATH="python3"
    fi

    echo "Using Python: $PYTHON_PATH"

    # Install using the same Python that pm2 uses
    if [[ "$PYTHON_PATH" == *"venv"* ]]; then
        VENV_DIR=$(dirname $(dirname $PYTHON_PATH))
        echo "Detected virtualenv at: $VENV_DIR"
        $VENV_DIR/bin/pip install finnhub-python>=2.4.0 yfinance>=0.2.40
    else
        $PYTHON_PATH -m pip install --user finnhub-python>=2.4.0 yfinance>=0.2.40
    fi
else
    echo "Backend not running with pm2, installing globally..."
    pip3 install finnhub-python>=2.4.0 yfinance>=0.2.40
fi

echo ""

echo -e "${YELLOW}Step 2: Pulling latest code with yfinance fallback...${NC}"
git pull origin claude/evaluate-html-to-react-011CV429JWyi22JWAMhZUBox
echo ""

echo -e "${YELLOW}Step 3: Restarting backend to load new modules...${NC}"
pm2 restart ai-search-backend
sleep 5
echo ""

echo -e "${YELLOW}Step 4: Fetching ZBIO historical data...${NC}"
echo "Triggering historical data fetch for ZBIO..."
RESPONSE=$(curl -s -X POST http://localhost:8000/api/stocks/ZBIO/update-history)
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"

NEW_RECORDS=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('new_records', 0))" 2>/dev/null)
echo ""
echo "New records fetched: $NEW_RECORDS"
echo ""

echo -e "${YELLOW}Step 5: Verifying database...${NC}"
RESPONSE=$(curl -s "http://localhost:8000/api/stocks/ZBIO/history?days=365")
COUNT=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('count', 0))" 2>/dev/null)

if [ "$COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ SUCCESS: ZBIO has $COUNT historical records${NC}"
else
    echo -e "${RED}✗ FAILED: ZBIO still has no historical data${NC}"
    echo ""
    echo "Checking backend logs for errors:"
    pm2 logs ai-search-backend --lines 20 --nostream
fi
echo ""

echo "=========================================="
echo "Fix Complete"
echo "=========================================="
echo ""
echo "Summary:"
echo "  - Installed finnhub-python and yfinance in backend environment"
echo "  - Added yfinance fallback for US stock historical data"
echo "  - Finnhub free tier only supports current prices, not historical"
echo "  - yfinance provides free historical data for US stocks"
