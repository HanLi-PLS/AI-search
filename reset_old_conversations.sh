#!/bin/bash

# Reset old conversations to NULL user_id
# This hides them from all users since we can't determine ownership

set -e

echo "=========================================="
echo "Reset Old Conversations"
echo "=========================================="
echo ""

DB_PATH="/opt/ai-search/data/db/search_jobs.db"

if [ ! -f "$DB_PATH" ]; then
    echo "Error: Database not found at $DB_PATH"
    exit 1
fi

# Show current state
echo "Current state:"
echo "--------------"
sqlite3 -header -column "$DB_PATH" "
    SELECT user_id, COUNT(*) as total_searches, COUNT(DISTINCT conversation_id) as conversations
    FROM search_jobs
    GROUP BY user_id;
"
echo ""

# Reset all user_ids back to NULL
echo "Resetting all user_ids to NULL (hiding old conversations)..."
UPDATED=$(sqlite3 "$DB_PATH" "UPDATE search_jobs SET user_id = NULL; SELECT changes();")
echo "Updated $UPDATED rows"
echo ""

# Show new state
echo "After reset:"
echo "------------"
sqlite3 -header -column "$DB_PATH" "
    SELECT
        CASE WHEN user_id IS NULL THEN 'NULL' ELSE CAST(user_id AS TEXT) END as user_id,
        COUNT(*) as total_searches,
        COUNT(DISTINCT conversation_id) as conversations
    FROM search_jobs
    GROUP BY user_id;
"
echo ""

echo "=========================================="
echo "Reset Complete!"
echo "=========================================="
echo ""
echo "What this means:"
echo "- All old conversations are now hidden (user_id = NULL)"
echo "- New searches will automatically get the correct user_id"
echo "- Each user will start fresh with proper conversation filtering"
echo ""
