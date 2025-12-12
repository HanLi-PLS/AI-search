#!/bin/bash

# Debug script to verify conversation filtering is working correctly

echo "=========================================="
echo "Conversation History Debug Report"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check database state
echo "1. Database State:"
echo "   Total search jobs:"
sqlite3 /opt/ai-search/data/db/search_jobs.db "SELECT COUNT(*) FROM search_jobs;"

echo "   Jobs by user_id:"
sqlite3 /opt/ai-search/data/db/search_jobs.db "SELECT user_id, COUNT(*) as count FROM search_jobs GROUP BY user_id;"

echo "   Jobs with NULL user_id:"
sqlite3 /opt/ai-search/data/db/search_jobs.db "SELECT COUNT(*) FROM search_jobs WHERE user_id IS NULL;"

echo ""

# Check distinct conversation IDs for user_id=1
echo "2. Conversations for user_id=1:"
sqlite3 /opt/ai-search/data/db/search_jobs.db "SELECT COUNT(DISTINCT conversation_id) FROM search_jobs WHERE user_id = 1 AND conversation_id IS NOT NULL;"

echo "   (This should match what API returns)"
echo ""

# Check if backend is running
echo "3. Backend Status:"
pm2 info backend | grep -E "(status|uptime|restart)"
echo ""

# Check frontend build timestamp
echo "4. Frontend Build Time:"
stat -c "%y" /opt/ai-search/frontend/dist/index.html 2>/dev/null || echo "   Frontend not built yet!"
echo ""

# Check nginx config
echo "5. Nginx Configuration:"
nginx -t 2>&1 | grep -E "(successful|failed)"
echo ""

# Test API without authentication
echo "6. API Test (no auth - should fail with 401):"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/conversations)
if [ "$HTTP_CODE" = "401" ]; then
    echo -e "   ${GREEN}✓ Authentication required (correct)${NC}"
else
    echo -e "   ${RED}✗ Got HTTP $HTTP_CODE (should be 401)${NC}"
fi
echo ""

echo "=========================================="
echo "Debug Report Complete"
echo "=========================================="
echo ""
echo "To test with authentication:"
echo "1. Get your auth token from browser:"
echo "   - Open Dev Console (F12)"
echo "   - Go to Application → Local Storage"
echo "   - Copy value of 'authToken'"
echo ""
echo "2. Test API:"
echo "   curl -H 'Authorization: Bearer YOUR_TOKEN' http://localhost:8000/api/conversations"
echo ""
