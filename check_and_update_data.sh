#!/bin/bash
# Script to check latest data and update if needed

echo "=============================================="
echo "Checking Latest Stock Data"
echo "Current Time: $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "=============================================="

API_URL="http://localhost:8000/api"

echo ""
echo "1. Checking database statistics..."
echo "----------------------------------------------"
curl -s "${API_URL}/stocks/history/stats" | python3 -m json.tool | head -20

echo ""
echo "2. Checking a sample stock (2561.HK)..."
echo "----------------------------------------------"
curl -s "${API_URL}/stocks/price/2561.HK" | python3 -m json.tool

echo ""
echo "3. Getting latest historical data for 2561.HK..."
echo "----------------------------------------------"
curl -s "${API_URL}/stocks/2561.HK/history?days=5" | python3 -m json.tool | grep -A 10 '"data":'

echo ""
echo "=============================================="
echo "To update all stocks with today's data, run:"
echo "curl -X POST ${API_URL}/stocks/bulk-update-history"
echo "=============================================="
