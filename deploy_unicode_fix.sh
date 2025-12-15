#!/bin/bash

# Deploy Unicode fix for Chinese character rendering
# Run this on the production server

set -e  # Exit on error

echo "=========================================="
echo "Deploying Unicode Fix"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo "Error: Must run from /opt/ai-search directory"
    exit 1
fi

# Step 1: Pull latest code
echo "1. Pulling latest code from branch..."
git fetch origin claude/upgrade-document-search-0146g7aVkVoKHACRKoW3X4y4
git pull origin claude/upgrade-document-search-0146g7aVkVoKHACRKoW3X4y4
echo -e "${GREEN}✓ Code updated${NC}"
echo ""

# Step 2: Restart backend service
echo "2. Restarting backend service..."
pm2 restart ai-search-backend
echo -e "${GREEN}✓ Backend restarted${NC}"
echo ""

# Step 3: Show status
echo "3. Checking service status..."
pm2 status
echo ""

echo "=========================================="
echo -e "${GREEN}Unicode Fix Deployed!${NC}"
echo "=========================================="
echo ""
echo "Chinese characters should now display properly in search results."
echo ""
echo "To view logs: pm2 logs ai-search-backend"
echo ""
