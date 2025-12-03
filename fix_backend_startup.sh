#!/bin/bash
# Fix backend startup issues

echo "=============================================="
echo "Checking Backend Startup Issues"
echo "=============================================="
echo ""

# Check PM2 status
echo "1. PM2 Status:"
pm2 status
echo ""

# Check PM2 logs for errors
echo "2. Recent Backend Logs (last 30 lines):"
pm2 logs ai-search-backend --lines 30 --nostream
echo ""

# Check if port 8000 is in use
echo "3. Port 8000 Status:"
lsof -i :8000 || echo "Port 8000 is not in use"
echo ""

# Check Python process
echo "4. Python Processes:"
ps aux | grep uvicorn | grep -v grep || echo "No uvicorn processes found"
echo ""

echo "=============================================="
echo "Common Issues & Fixes:"
echo "=============================================="
echo ""
echo "If you see import errors:"
echo "  cd /opt/ai-search/backend"
echo "  source venv/bin/activate"
echo "  pip install -r requirements.txt"
echo ""
echo "If you see permission errors:"
echo "  sudo chown -R ec2-user:ec2-user /opt/ai-search"
echo ""
echo "To manually test backend:"
echo "  cd /opt/ai-search/backend"
echo "  source venv/bin/activate"
echo "  uvicorn main:app --host 0.0.0.0 --port 8000"
echo ""
