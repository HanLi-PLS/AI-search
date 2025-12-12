#!/bin/bash

# Deploy conversation history security fix
# This script deploys the localStorage contamination fix

set -e  # Exit on error

echo "=========================================="
echo "Deploying Conversation History Security Fix"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Step 1: Pull latest code
echo "1. Pulling latest code..."
cd /opt/ai-search
git fetch origin
git pull origin claude/upgrade-document-search-0146g7aVkVoKHACRKoW3X4y4
echo -e "${GREEN}✓ Code updated${NC}"
echo ""

# Step 2: Rebuild frontend with cache busting
echo "2. Rebuilding frontend (with cache clear)..."
cd frontend
rm -rf node_modules/.vite  # Clear Vite cache
rm -rf dist  # Clear old build
npm run build
echo -e "${GREEN}✓ Frontend rebuilt${NC}"
echo ""

# Step 3: Restart nginx to clear any caching
echo "3. Restarting nginx..."
sudo systemctl restart nginx
echo -e "${GREEN}✓ Nginx restarted${NC}"
echo ""

# Step 4: Verify backend is running with latest code
echo "4. Checking backend status..."
cd /opt/ai-search
pm2 restart backend
sleep 3
pm2 status
echo -e "${GREEN}✓ Backend restarted${NC}"
echo ""

# Step 5: Test API endpoint
echo "5. Testing API endpoint (should return user-filtered conversations)..."
TOKEN=$(cat .env | grep -v "^#" | grep "TEST_AUTH_TOKEN" | cut -d'=' -f2 || echo "")
if [ -z "$TOKEN" ]; then
    echo -e "${YELLOW}Note: No TEST_AUTH_TOKEN found. Get your token from browser localStorage.${NC}"
else
    echo "Testing with token..."
    curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/conversations | jq '.conversations | length'
fi
echo ""

echo "=========================================="
echo -e "${GREEN}Deployment Complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Open browser to your site"
echo "2. Press Ctrl+Shift+R (or Cmd+Shift+R on Mac) for hard refresh"
echo "3. Open Developer Console (F12)"
echo "4. Go to Application tab → Local Storage"
echo "5. Delete 'chatHistory' and 'currentConversationId' entries"
echo "6. Refresh page again"
echo ""
echo "You should now see only YOUR conversations (user_id=1)"
echo ""
