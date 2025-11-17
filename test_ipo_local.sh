#!/bin/bash
echo "=========================================="
echo "Testing IPO Tracker Endpoint (Local)"
echo "=========================================="

echo ""
echo "Step 1: Test the API endpoint from localhost"
echo "------------------------------------------------------------"
curl -s http://localhost:8000/api/stocks/upcoming-ipos | python3 -m json.tool | head -50

echo ""
echo ""
echo "Step 2: Check backend logs for IPO-related messages"
echo "------------------------------------------------------------"
pm2 logs ai-search-backend --nostream --lines 30 | grep -i "ipo\|s3\|cache" || echo "No IPO logs found"

echo ""
echo ""
echo "Step 3: Clear IPO cache files"
echo "------------------------------------------------------------"
echo "Looking for cache files..."
find /opt/ai-search -name "*ipo*cache*" -type f 2>/dev/null || echo "No cache files found"

echo ""
echo "If the API shows format: 'html', the in-memory cache needs clearing"
echo "Solution: pm2 restart ai-search-backend"
echo "=========================================="
