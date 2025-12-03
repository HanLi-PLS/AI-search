#!/bin/bash

echo "=========================================="
echo "IPO Performance Diagnostics"
echo "=========================================="
echo ""

# Check CSV file size on S3
echo "1. Checking CSV file size on S3..."
aws s3 ls s3://plfs-han-ai-search/public_company_tracker/hkex_ipo_tracker/hkex_ipo_2025_v20251113.csv --human-readable 2>/dev/null || echo "Cannot access S3 file"
echo ""

# Time the API endpoint
echo "2. Testing API endpoint performance..."
echo "Making request to: http://localhost:8000/api/stocks/upcoming-ipos"
START=$(date +%s.%N)
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}\nTIME_TOTAL:%{time_total}\n" http://localhost:8000/api/stocks/upcoming-ipos)
END=$(date +%s.%N)
ELAPSED=$(echo "$END - $START" | bc)

HTTP_CODE=$(echo "$RESPONSE" | grep HTTP_CODE | cut -d: -f2)
TIME_TOTAL=$(echo "$RESPONSE" | grep TIME_TOTAL | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE/d' | sed '/TIME_TOTAL/d')

echo "HTTP Status: $HTTP_CODE"
echo "Response Time: ${TIME_TOTAL}s"
echo ""

if [ "$HTTP_CODE" = "200" ]; then
    echo "3. Analyzing response..."
    COUNT=$(echo "$BODY" | python3 -c "import sys, json; print(json.load(sys.stdin).get('count', 0))" 2>/dev/null)
    SUCCESS=$(echo "$BODY" | python3 -c "import sys, json; print(json.load(sys.stdin).get('success', False))" 2>/dev/null)

    echo "Success: $SUCCESS"
    echo "Record count: $COUNT"
    echo ""

    if [ "$COUNT" -gt 100 ]; then
        echo "⚠️  WARNING: Large number of records ($COUNT)"
        echo "This could cause slow loading. Consider:"
        echo "  - Adding pagination"
        echo "  - Implementing lazy loading"
        echo "  - Reducing columns displayed"
    fi
else
    echo "❌ Error response from server"
    echo "$BODY" | head -20
fi

echo ""
echo "4. Checking backend logs for errors..."
pm2 logs ai-search-backend --lines 20 --nostream | grep -i "error\|exception\|slow" || echo "No errors found"

echo ""
echo "=========================================="
echo "Performance Tips:"
echo "=========================================="
echo ""
echo "If loading is slow:"
echo "1. Large file? Consider filtering data before sending to frontend"
echo "2. Many columns? Only send necessary columns"
echo "3. Check S3 region - should be same as EC2 for speed"
echo "4. Add caching to avoid repeated S3 downloads"
echo "5. Consider pagination for large datasets"
