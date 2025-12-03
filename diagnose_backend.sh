#!/bin/bash
echo "=========================================="
echo "Stock Tracker Backend Diagnostics"
echo "=========================================="

echo ""
echo "1. Check pm2 status"
echo "------------------------------------------------------------"
pm2 status

echo ""
echo "2. Check backend logs for errors"
echo "------------------------------------------------------------"
pm2 logs ai-search-backend --nostream --lines 50 | tail -30

echo ""
echo "3. Test backend health"
echo "------------------------------------------------------------"
curl -s http://localhost:8000/health || echo "Health endpoint not responding"

echo ""
echo "4. Test stock API endpoint"
echo "------------------------------------------------------------"
curl -s http://localhost:8000/api/stocks/prices | head -c 500 || echo "Stock prices endpoint not responding"

echo ""
echo "5. Check if backend process is listening on port 8000"
echo "------------------------------------------------------------"
netstat -tlnp 2>/dev/null | grep 8000 || ss -tlnp 2>/dev/null | grep 8000 || echo "Port 8000 not in use"

echo ""
echo "=========================================="
echo "Diagnostics Complete"
echo "=========================================="
