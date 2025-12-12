#!/bin/bash

# Check conversation IDs and counts per user

echo "=========================================="
echo "Conversation Analysis"
echo "=========================================="
echo ""

DB_PATH="/opt/ai-search/data/db/search_jobs.db"

if [ ! -f "$DB_PATH" ]; then
    echo "Error: Database not found at $DB_PATH"
    exit 1
fi

echo "1. Total conversations per user:"
echo "   (conversation_id, user_id, search_count)"
echo "   ----------------------------------------"
sqlite3 -header -column "$DB_PATH" "
    SELECT
        conversation_id,
        user_id,
        COUNT(*) as search_count,
        MIN(created_at) as first_search,
        MAX(updated_at) as last_updated
    FROM search_jobs
    WHERE conversation_id IS NOT NULL
    GROUP BY conversation_id, user_id
    ORDER BY user_id, last_updated DESC;
"
echo ""

echo "2. Summary by user:"
echo "   -----------------"
sqlite3 -header -column "$DB_PATH" "
    SELECT
        user_id,
        COUNT(DISTINCT conversation_id) as total_conversations,
        COUNT(*) as total_searches
    FROM search_jobs
    WHERE conversation_id IS NOT NULL
    GROUP BY user_id
    ORDER BY user_id;
"
echo ""

echo "3. Conversations for user_id=1 (YOUR conversations):"
echo "   ---------------------------------------------------"
sqlite3 -header -column "$DB_PATH" "
    SELECT
        conversation_id,
        COUNT(*) as search_count,
        MIN(query) as first_query,
        MAX(updated_at) as last_updated
    FROM search_jobs
    WHERE conversation_id IS NOT NULL AND user_id = 1
    GROUP BY conversation_id
    ORDER BY last_updated DESC
    LIMIT 20;
"
echo ""

echo "4. Jobs with NULL user_id (SECURITY ISSUE if any):"
echo "   -------------------------------------------------"
NULL_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM search_jobs WHERE user_id IS NULL;")
if [ "$NULL_COUNT" -gt 0 ]; then
    echo "   ⚠️  WARNING: Found $NULL_COUNT jobs with NULL user_id"
    sqlite3 -header -column "$DB_PATH" "
        SELECT job_id, conversation_id, query, created_at
        FROM search_jobs
        WHERE user_id IS NULL
        LIMIT 10;
    "
else
    echo "   ✓ No NULL user_ids found (good!)"
fi
echo ""

echo "5. Distinct conversation IDs across all users:"
echo "   ---------------------------------------------"
sqlite3 "$DB_PATH" "SELECT COUNT(DISTINCT conversation_id) FROM search_jobs WHERE conversation_id IS NOT NULL;"
echo ""

echo "=========================================="
echo "Analysis Complete"
echo "=========================================="
