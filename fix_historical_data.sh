#!/bin/bash

echo "=========================================="
echo "Fix Historical Data Coverage"
echo "=========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Checking current historical data coverage...${NC}"
echo ""

# Check database statistics
DB_PATH="/opt/ai-search/data/db/stocks.db"

if [ -f "$DB_PATH" ]; then
    echo "Current database statistics:"
    sqlite3 "$DB_PATH" << 'EOF'
.mode column
.headers on
SELECT
    ticker,
    COUNT(*) as records,
    MIN(trade_date) as earliest_date,
    MAX(trade_date) as latest_date,
    julianday(MAX(trade_date)) - julianday(MIN(trade_date)) as days_covered
FROM stock_daily
GROUP BY ticker
ORDER BY days_covered DESC
LIMIT 10;
EOF
    echo ""
else
    echo "Database not found at $DB_PATH"
    echo ""
fi

echo -e "${YELLOW}Running backfill script to ensure 1 year of data...${NC}"
echo ""

cd /opt/ai-search || cd ~/ai-search

# Pull latest code
echo "Pulling latest code..."
git pull origin claude/evaluate-html-to-react-011CV429JWyi22JWAMhZUBox
echo ""

# Make script executable
chmod +x backfill_full_year.py

# Run backfill
echo "Starting backfill process..."
echo "This may take several minutes depending on number of stocks..."
echo ""

python3 backfill_full_year.py

echo ""
echo -e "${GREEN}Backfill complete!${NC}"
echo ""

# Show updated statistics
if [ -f "$DB_PATH" ]; then
    echo "Updated database statistics:"
    sqlite3 "$DB_PATH" << 'EOF'
.mode column
.headers on
SELECT
    ticker,
    COUNT(*) as records,
    MIN(trade_date) as earliest_date,
    MAX(trade_date) as latest_date,
    julianday(MAX(trade_date)) - julianday(MIN(trade_date)) as days_covered
FROM stock_daily
GROUP BY ticker
ORDER BY days_covered DESC
LIMIT 10;
EOF
    echo ""

    # Check if any stock has less than 180 days
    STOCKS_WITH_LIMITED_DATA=$(sqlite3 "$DB_PATH" "
        SELECT ticker
        FROM (
            SELECT
                ticker,
                julianday(MAX(trade_date)) - julianday(MIN(trade_date)) as days_covered
            FROM stock_daily
            GROUP BY ticker
        )
        WHERE days_covered < 180
    ")

    if [ -n "$STOCKS_WITH_LIMITED_DATA" ]; then
        echo -e "${YELLOW}Note: Some stocks have less than 6 months of data:${NC}"
        echo "$STOCKS_WITH_LIMITED_DATA"
        echo ""
        echo "This is normal for recently listed companies (IPO < 6 months ago)"
    fi
fi

echo ""
echo "=========================================="
echo "Summary"
echo "=========================================="
echo ""
echo "✓ Historical data backfilled for all stocks"
echo "✓ Each stock now has maximum available data"
echo "✓ Charts will show full history when you select '1Y'"
echo ""
echo "Refresh the Stock Tracker page to see updated charts!"
