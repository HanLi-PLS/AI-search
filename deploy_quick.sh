#!/bin/bash

# Quick deploy script for EC2 security updates
# Run this after git pull to update everything

set -e  # Exit on error

echo "=========================================="
echo "Deploying Security Updates"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo "Error: Must run from project root directory"
    exit 1
fi

# Step 1: Pull latest code
echo "1. Pulling latest code..."
git fetch origin
git pull origin claude/evaluate-html-to-react-01D6i6R5AMZQrJChq2S5j3J1
echo -e "${GREEN}✓ Code updated${NC}"
echo ""

# Step 2: Update backend dependencies
echo "2. Updating backend dependencies..."
source venv/bin/activate
pip install -r requirements.txt --quiet
echo -e "${GREEN}✓ Backend dependencies updated${NC}"
echo ""

# Step 3: Update frontend dependencies
echo "3. Updating frontend dependencies..."
cd frontend
npm install --quiet
echo -e "${GREEN}✓ Frontend dependencies updated${NC}"
echo ""

# Step 4: Rebuild frontend
echo "4. Building frontend..."
npm run build
cd ..
echo -e "${GREEN}✓ Frontend built${NC}"
echo ""

# Step 5: Configure security settings
echo "5. Configuring security settings..."
if [ -f ".env" ]; then
    echo -e "${YELLOW}Existing .env found. Running security setup...${NC}"
else
    echo "No .env file found. Running security setup..."
fi
./setup_security.sh
echo ""

# Step 6: Restart services
echo "6. Restarting services..."
pm2 restart all
echo -e "${GREEN}✓ Services restarted${NC}"
echo ""

# Step 7: Show status
echo "7. Checking service status..."
pm2 status
echo ""

echo "=========================================="
echo -e "${GREEN}Deployment Complete!${NC}"
echo "=========================================="
echo ""
echo "To view logs: pm2 logs"
echo "To check status: pm2 status"
echo ""
