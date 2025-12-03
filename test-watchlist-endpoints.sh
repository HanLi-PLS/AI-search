#!/bin/bash
# Test script for watchlist management endpoints

echo "=== Watchlist Management API Test ==="
echo ""

# Set your token here (get from login)
if [ -z "$TOKEN" ]; then
    echo "ERROR: TOKEN environment variable not set"
    echo "Please run: export TOKEN='your-auth-token'"
    exit 1
fi

BASE_URL="http://localhost:8000/api/watchlist"

echo "1. Testing company search..."
echo "   Searching for 'Apple' in US market..."
curl -s -X GET "${BASE_URL}/search?query=Apple&market=US&limit=5" \
  -H "Authorization: Bearer $TOKEN" | jq '.companies[] | {ticker, companyname, exchange_name}'

echo ""
echo "2. Adding AAPL to watchlist..."
curl -s -X POST "${BASE_URL}/add?ticker=AAPL&market=US" \
  -H "Authorization: Bearer $TOKEN" | jq

echo ""
echo "3. Adding Tencent (700.HK) to watchlist..."
curl -s -X POST "${BASE_URL}/add?ticker=700&market=HK" \
  -H "Authorization: Bearer $TOKEN" | jq

echo ""
echo "4. Getting watchlist..."
curl -s -X GET "${BASE_URL}/list" \
  -H "Authorization: Bearer $TOKEN" | jq

echo ""
echo "5. Getting company details for AAPL..."
curl -s -X GET "${BASE_URL}/company/AAPL?market=US" \
  -H "Authorization: Bearer $TOKEN" | jq '.company | {companyname, ticker, price_close, market_cap, pricing_date}'

echo ""
echo "6. Removing AAPL from watchlist..."
curl -s -X DELETE "${BASE_URL}/remove?ticker=AAPL&market=US" \
  -H "Authorization: Bearer $TOKEN" | jq

echo ""
echo "7. Getting watchlist again (should only have Tencent)..."
curl -s -X GET "${BASE_URL}/list" \
  -H "Authorization: Bearer $TOKEN" | jq '.companies[] | {ticker, company_name, market}'

echo ""
echo "=== Test Complete ==="
