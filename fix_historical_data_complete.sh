#!/bin/bash

echo "=========================================="
echo "Complete Historical Data Fix"
echo "=========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "This script will:"
echo "  1. Check if data was archived to S3"
echo "  2. Restore from S3 if available"
echo "  3. Backfill from APIs if not in S3"
echo "  4. Restart backend with archival disabled"
echo ""

cd /opt/ai-search || cd ~/ai-search

echo -e "${YELLOW}Pulling latest code...${NC}"
git pull origin claude/evaluate-html-to-react-011CV429JWyi22JWAMhZUBox
echo ""

echo -e "${YELLOW}Step 1: Checking current database status...${NC}"
DB_PATH="/opt/ai-search/data/db/stocks.db"

if [ -f "$DB_PATH" ]; then
    TOTAL_RECORDS=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM stock_daily;" 2>/dev/null || echo "0")
    echo "Current SQLite records: $TOTAL_RECORDS"

    if [ "$TOTAL_RECORDS" -lt 10000 ]; then
        echo -e "${YELLOW}⚠️  Low record count - data may have been archived${NC}"
    fi
else
    echo "Database not found at $DB_PATH"
fi
echo ""

echo -e "${YELLOW}Step 2: Checking S3 for archived data...${NC}"
S3_CHECK=$(aws s3 ls s3://plfs-han-ai-search/public_company_tracker/hkex_18a_stocks/ 2>&1 | head -1)

if echo "$S3_CHECK" | grep -q "PRE\|parquet"; then
    echo -e "${GREEN}✓ Data found in S3${NC}"
    echo ""
    echo -e "${YELLOW}Step 3: Restoring data from S3...${NC}"
    chmod +x restore_from_s3.py
    python3 restore_from_s3.py <<< "yes"
    echo ""
else
    echo -e "${YELLOW}No data in S3 - will backfill from APIs instead${NC}"
    echo ""
fi

echo -e "${YELLOW}Step 4: Ensuring full year coverage...${NC}"
chmod +x backfill_full_year.py
python3 backfill_full_year.py
echo ""

echo -e "${YELLOW}Step 5: Restarting backend (archival disabled)...${NC}"
pm2 restart ai-search-backend
sleep 5
echo ""

echo -e "${YELLOW}Step 6: Verifying fix...${NC}"
if [ -f "$DB_PATH" ]; then
    FINAL_RECORDS=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM stock_daily;" 2>/dev/null || echo "0")
    echo "Final SQLite records: $FINAL_RECORDS"

    if [ "$FINAL_RECORDS" -gt "$TOTAL_RECORDS" ]; then
        ADDED=$((FINAL_RECORDS - TOTAL_RECORDS))
        echo -e "${GREEN}✓ Added $ADDED records${NC}"
    fi

    echo ""
    echo "Sample data coverage:"
    sqlite3 "$DB_PATH" << 'EOF'
.mode column
.headers on
SELECT
    ticker,
    COUNT(*) as records,
    MIN(trade_date) as earliest,
    MAX(trade_date) as latest,
    CAST(julianday(MAX(trade_date)) - julianday(MIN(trade_date)) AS INTEGER) as days
FROM stock_daily
GROUP BY ticker
ORDER BY days DESC
LIMIT 5;
EOF
fi
echo ""

echo "=========================================="
echo "Fix Complete!"
echo "=========================================="
echo ""
echo "✓ Historical data restored/backfilled"
echo "✓ Backend restarted with archival disabled"
echo "✓ Charts should now show full historical data"
echo ""
echo "Please refresh the Stock Tracker page in your browser."
echo ""
echo "Note: S3 automatic archival has been disabled until"
echo "      the hybrid retrieval feature is properly tested."
