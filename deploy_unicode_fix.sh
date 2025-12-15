#!/bin/bash

# Deploy Unicode fix and auto-scroll feature
# Run this on the production server

set -e  # Exit on error

echo "=========================================="
echo "Deploying Updates"
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

# Step 2: Build frontend
echo "2. Building frontend..."
cd frontend
npm run build
cd ..
echo -e "${GREEN}✓ Frontend built${NC}"
echo ""

# Step 3: Restart backend service
echo "3. Restarting backend service..."
pm2 restart ai-search-backend
echo -e "${GREEN}✓ Backend restarted${NC}"
echo ""

# Step 4: Show status
echo "4. Checking service status..."
pm2 status
echo ""

echo "=========================================="
echo -e "${GREEN}Deployment Complete!${NC}"
echo "=========================================="
echo ""
echo "Updates deployed:"
echo "  ✓ Unicode fix - Chinese characters display properly"
echo "  ✓ Auto-scroll - Latest messages auto-scroll into view"
echo ""
echo "To view logs: pm2 logs ai-search-backend"
echo ""
