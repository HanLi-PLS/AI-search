#!/bin/bash

echo "==========================================="
echo "Portfolio Companies Feature Deployment"
echo "==========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Step 1: Installing dependencies...${NC}"
echo "Installing finnhub-python for NASDAQ stock data..."
pip3 install finnhub-python>=2.4.0 || echo -e "${RED}Warning: finnhub-python installation failed${NC}"
echo ""

echo -e "${YELLOW}Step 2: Pulling latest code...${NC}"
git fetch origin claude/evaluate-html-to-react-011CV429JWyi22JWAMhZUBox
git pull origin claude/evaluate-html-to-react-011CV429JWyi22JWAMhZUBox
echo ""

echo -e "${YELLOW}Step 3: Restarting backend...${NC}"
pm2 restart ai-search-backend
sleep 3
echo ""

echo -e "${YELLOW}Step 4: Rebuilding frontend...${NC}"
cd frontend
npm run build
cd ..
echo ""

echo -e "${YELLOW}Step 5: Restarting frontend...${NC}"
pm2 restart ai-search-frontend
sleep 2
echo ""

echo -e "${YELLOW}Step 6: Testing portfolio endpoint...${NC}"
echo "Making request to: http://localhost:8000/api/stocks/portfolio"
RESPONSE=$(curl -s http://localhost:8000/api/stocks/portfolio)
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

SUCCESS=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('success', False))" 2>/dev/null)
if [ "$SUCCESS" = "True" ]; then
    echo -e "${GREEN}✓ Portfolio endpoint is working!${NC}"
    COUNT=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('count', 0))" 2>/dev/null)
    echo "Companies returned: $COUNT"
else
    echo -e "${RED}✗ Portfolio endpoint returned success=False${NC}"
fi
echo ""

echo -e "${YELLOW}Step 7: Initializing historical data for portfolio companies...${NC}"
chmod +x init_portfolio_history.sh
./init_portfolio_history.sh
echo ""

echo "==========================================="
echo "Summary of Changes"
echo "==========================================="
echo ""
echo "Files created:"
echo "  - backend/app/services/portfolio.py"
echo ""
echo "Files modified:"
echo "  - backend/app/api/routes/stocks.py (added /api/stocks/portfolio endpoint)"
echo "  - frontend/src/services/api.js (added getPortfolioCompanies())"
echo "  - frontend/src/pages/StockTracker.jsx (implemented Portfolio Companies tab)"
echo ""
echo "Portfolio companies tracked:"
echo "  1. Visen Pharmaceuticals (02561.HK) - HKEX"
echo "  2. Zenas Biopharma (ZBIO) - NASDAQ"
echo ""
echo "Data sources:"
echo "  - HKEX stocks: Tushare Pro API"
echo "  - NASDAQ stocks: Finnhub API (primary), Tushare/yfinance (fallback)"
echo "  - Finnhub requires API key from AWS Secrets Manager: finnhub-api-key"
echo ""
echo "Deployment complete!"
echo "Visit the Stock Tracker and click the 'Portfolio Companies' tab to see the results."
