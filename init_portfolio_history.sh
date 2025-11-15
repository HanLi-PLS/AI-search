#!/bin/bash

echo "=========================================="
echo "Initialize Historical Data for Portfolio Companies"
echo "=========================================="
echo ""

# Portfolio companies
COMPANIES=("2561.HK" "ZBIO")

for TICKER in "${COMPANIES[@]}"; do
    echo "Fetching historical data for $TICKER..."

    # Trigger update (will fetch 365 days on first run)
    RESPONSE=$(curl -s -X POST "http://localhost:8000/api/stocks/$TICKER/update-history")

    echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'  ✓ {data.get(\"ticker\")}: {data.get(\"new_records\")} records fetched')" 2>/dev/null || echo "  ✗ Failed"

    echo ""
done

echo "=========================================="
echo "Checking data in database..."
echo ""

for TICKER in "${COMPANIES[@]}"; do
    # Get history stats
    RESPONSE=$(curl -s "http://localhost:8000/api/stocks/$TICKER/history?days=365")

    COUNT=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('count', 0))" 2>/dev/null)

    if [ "$COUNT" -gt 0 ]; then
        echo "✓ $TICKER: $COUNT historical records available"
    else
        echo "✗ $TICKER: No historical data found"
    fi
done

echo ""
echo "=========================================="
echo "Initialization complete!"
echo "Portfolio companies should now have historical charts."
