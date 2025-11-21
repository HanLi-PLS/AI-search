#!/bin/bash
# Helper script to test the debug-exchanges endpoint

echo "=== Testing CapIQ Debug Exchanges Endpoint ==="
echo ""

# Pull latest changes
echo "1. Pulling latest changes..."
git pull origin claude/evaluate-html-to-react-01D6i6R5AMZQrJChq2S5j3J1

# Restart backend
echo ""
echo "2. Restarting backend..."
pm2 restart ai-search-backend

# Wait for backend to start
echo ""
echo "3. Waiting for backend to start (5 seconds)..."
sleep 5

# Get auth token (you'll need to log in first if you don't have a token)
echo ""
echo "4. To get an auth token, first log in:"
echo "   curl -X POST http://localhost:8000/api/auth/login \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"email\": \"your-email@example.com\", \"password\": \"your-password\"}' | jq -r '.access_token'"
echo ""
echo "5. Then run the debug endpoint:"
echo "   TOKEN='your-token-here'"
echo "   curl -X GET 'http://localhost:8000/api/watchlist/debug-exchanges' \\"
echo "     -H 'Authorization: Bearer \$TOKEN' | jq"
echo ""
echo "=== OR run the debug endpoint directly if backend doesn't require auth ==="
curl -X GET 'http://localhost:8000/api/watchlist/debug-exchanges' 2>/dev/null | jq '.' || echo "Authentication required. Please get a token first."
