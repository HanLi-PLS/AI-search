#!/bin/bash

# Quick script to test IPO endpoint and see what's wrong

echo "Testing IPO endpoint..."
echo ""

# Test the endpoint
echo "Calling: http://localhost:8000/api/stocks/upcoming-ipos"
curl -v http://localhost:8000/api/stocks/upcoming-ipos 2>&1 | head -100

echo ""
echo ""
echo "Checking backend logs for errors:"
pm2 logs ai-search-backend --lines 30 --nostream | grep -i "error\|exception\|traceback" || echo "No errors found in logs"

echo ""
echo "Checking if openpyxl is installed:"
python3 -c "import openpyxl; print('openpyxl is installed')" 2>&1 || echo "openpyxl is NOT installed - this is the problem!"

echo ""
echo "To fix: pip3 install openpyxl"
