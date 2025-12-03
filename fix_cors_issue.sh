#!/bin/bash
echo "=========================================="
echo "Fix AI Search CORS Issue"
echo "=========================================="

echo ""
echo "1. Checking current backend status"
echo "------------------------------------------------------------"
pm2 status ai-search-backend

echo ""
echo "2. Checking backend logs for errors"
echo "------------------------------------------------------------"
pm2 logs ai-search-backend --nostream --lines 30 | grep -i "error\|cors\|failed" || echo "No obvious errors found"

echo ""
echo "3. Restarting backend to reload CORS configuration"
echo "------------------------------------------------------------"
pm2 restart ai-search-backend

echo ""
echo "4. Waiting for backend to start..."
sleep 3

echo ""
echo "5. Testing CORS headers"
echo "------------------------------------------------------------"
curl -I -X OPTIONS http://localhost:8000/api/search \
  -H "Origin: http://34.219.223.181:5173" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" 2>&1 | grep -i "access-control" || echo "CORS headers not found"

echo ""
echo "6. Testing search endpoint directly"
echo "------------------------------------------------------------"
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "top_k": 5, "search_mode": "files_only", "reasoning_mode": "non_reasoning"}' 2>&1 | head -c 200

echo ""
echo ""
echo "=========================================="
echo "Restart Complete"
echo "=========================================="
echo "If CORS issue persists, the frontend might be cached."
echo "Try hard refresh (Ctrl+Shift+R) in your browser."
echo "=========================================="
