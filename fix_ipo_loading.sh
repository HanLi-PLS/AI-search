#!/bin/bash

# Script to diagnose and fix IPO loading issues

echo "=========================================="
echo "IPO Tracker Troubleshooting"
echo "=========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Check if openpyxl is installed
echo -e "${YELLOW}Step 1: Checking Python dependencies...${NC}"
if python3 -c "import openpyxl" 2>/dev/null; then
    echo -e "${GREEN}✓ openpyxl is installed${NC}"
else
    echo -e "${RED}✗ openpyxl is NOT installed${NC}"
    echo "Installing openpyxl..."
    pip3 install openpyxl
fi

if python3 -c "import pandas" 2>/dev/null; then
    echo -e "${GREEN}✓ pandas is installed${NC}"
else
    echo -e "${RED}✗ pandas is NOT installed${NC}"
    echo "Installing pandas..."
    pip3 install pandas
fi

if python3 -c "import boto3" 2>/dev/null; then
    echo -e "${GREEN}✓ boto3 is installed${NC}"
else
    echo -e "${RED}✗ boto3 is NOT installed${NC}"
    echo "Installing boto3..."
    pip3 install boto3
fi
echo ""

# Step 2: Check backend is running
echo -e "${YELLOW}Step 2: Checking backend status...${NC}"
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend is running${NC}"
else
    echo -e "${RED}✗ Backend is NOT running${NC}"
    echo "Starting backend..."
    pm2 restart ai-search-backend
    sleep 5
fi
echo ""

# Step 3: Check AWS credentials
echo -e "${YELLOW}Step 3: Checking AWS credentials...${NC}"
if aws sts get-caller-identity > /dev/null 2>&1; then
    echo -e "${GREEN}✓ AWS credentials are configured${NC}"
    aws sts get-caller-identity | grep -E "UserId|Account|Arn"
else
    echo -e "${RED}✗ AWS credentials NOT configured${NC}"
    echo "Please configure AWS credentials: aws configure"
fi
echo ""

# Step 4: Check S3 access
echo -e "${YELLOW}Step 4: Checking S3 bucket access...${NC}"
if aws s3 ls s3://plfs-han-ai-search/public_company_tracker/hkex_ipo_tracker/ > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Can access S3 bucket${NC}"
    echo "Files in bucket:"
    aws s3 ls s3://plfs-han-ai-search/public_company_tracker/hkex_ipo_tracker/
else
    echo -e "${RED}✗ Cannot access S3 bucket${NC}"
    echo "Check:"
    echo "  1. AWS credentials have S3 read permissions"
    echo "  2. Bucket name is correct: plfs-han-ai-search"
    echo "  3. EC2 instance has IAM role with S3 permissions"
fi
echo ""

# Step 5: Test the endpoint directly
echo -e "${YELLOW}Step 5: Testing IPO endpoint...${NC}"
echo "Making request to http://localhost:8000/api/stocks/upcoming-ipos"
echo ""

RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}\n" http://localhost:8000/api/stocks/upcoming-ipos)
HTTP_STATUS=$(echo "$RESPONSE" | grep HTTP_STATUS | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS/d')

echo "Status Code: $HTTP_STATUS"
echo ""
echo "Response body:"
echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
echo ""

if [ "$HTTP_STATUS" = "200" ]; then
    SUCCESS=$(echo "$BODY" | python3 -c "import sys, json; print(json.load(sys.stdin).get('success', False))" 2>/dev/null)
    if [ "$SUCCESS" = "True" ]; then
        echo -e "${GREEN}✓ Endpoint is working!${NC}"
        COUNT=$(echo "$BODY" | python3 -c "import sys, json; print(json.load(sys.stdin).get('count', 0))" 2>/dev/null)
        echo "Records returned: $COUNT"
    else
        echo -e "${RED}✗ Endpoint returned success=False${NC}"
        ERROR=$(echo "$BODY" | python3 -c "import sys, json; print(json.load(sys.stdin).get('error', 'Unknown'))" 2>/dev/null)
        echo "Error: $ERROR"
    fi
else
    echo -e "${RED}✗ Endpoint returned error status${NC}"
fi
echo ""

# Step 6: Check backend logs
echo -e "${YELLOW}Step 6: Recent backend logs (last 50 lines):${NC}"
pm2 logs ai-search-backend --lines 50 --nostream | tail -50
echo ""

# Step 7: Suggestions
echo -e "${YELLOW}=========================================="
echo "Troubleshooting Summary"
echo "==========================================${NC}"
echo ""

if [ "$HTTP_STATUS" = "200" ] && [ "$SUCCESS" = "True" ]; then
    echo -e "${GREEN}✓ Backend is working correctly!${NC}"
    echo ""
    echo "If frontend is still loading, try:"
    echo "1. Hard refresh browser: Ctrl+Shift+R (or Cmd+Shift+R on Mac)"
    echo "2. Clear browser cache"
    echo "3. Check browser console (F12) for JavaScript errors"
    echo "4. Make sure frontend is rebuilt:"
    echo "   cd /opt/ai-search/frontend && npm run build && pm2 restart ai-search-frontend"
else
    echo -e "${RED}Issue detected with backend/S3${NC}"
    echo ""
    echo "Common fixes:"
    echo "1. Ensure AWS credentials are configured:"
    echo "   aws configure"
    echo ""
    echo "2. Check EC2 IAM role has S3 read permissions"
    echo ""
    echo "3. Verify S3 bucket and file exist:"
    echo "   aws s3 ls s3://plfs-han-ai-search/public_company_tracker/hkex_ipo_tracker/"
    echo ""
    echo "4. Restart backend after fixing issues:"
    echo "   pm2 restart ai-search-backend"
fi
