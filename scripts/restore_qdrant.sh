#!/bin/bash
# Qdrant restore script - Restores from S3 backup or local snapshot
# Usage: ./restore_qdrant.sh [snapshot_file_or_s3_path]

set -e

COLLECTION_NAME="documents"

echo "=========================================="
echo "  QDRANT RESTORE UTILITY"
echo "  $(date)"
echo "=========================================="
echo ""

# Check if snapshot path is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <snapshot_file_or_s3_path>"
    echo ""
    echo "Examples:"
    echo "  $0 /tmp/qdrant_backup.snapshot"
    echo "  $0 s3://bucket/backups/qdrant/qdrant_documents_20250111_120000.snapshot"
    echo ""

    # List available S3 backups
    S3_BUCKET=$(grep "AWS_S3_BUCKET=" /opt/ai-search/.env 2>/dev/null | cut -d'=' -f2)
    if [ -n "$S3_BUCKET" ]; then
        echo "Available S3 backups:"
        aws s3 ls s3://$S3_BUCKET/backups/qdrant/ --human-readable | tail -10
    fi

    exit 1
fi

SNAPSHOT_PATH="$1"
LOCAL_SNAPSHOT="/tmp/qdrant_restore.snapshot"

# Download from S3 if needed
if [[ "$SNAPSHOT_PATH" == s3://* ]]; then
    echo "Downloading snapshot from S3..."
    aws s3 cp "$SNAPSHOT_PATH" "$LOCAL_SNAPSHOT"
    SNAPSHOT_PATH="$LOCAL_SNAPSHOT"
fi

# Verify snapshot file exists
if [ ! -f "$SNAPSHOT_PATH" ]; then
    echo "ERROR: Snapshot file not found: $SNAPSHOT_PATH"
    exit 1
fi

SNAPSHOT_SIZE=$(du -h "$SNAPSHOT_PATH" | cut -f1)
echo "Snapshot file: $SNAPSHOT_PATH ($SNAPSHOT_SIZE)"
echo ""

# Warning prompt
read -p "WARNING: This will replace the current collection. Continue? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Restore cancelled"
    exit 0
fi

echo ""
echo "Step 1: Stopping backend to prevent conflicts..."
npx pm2 stop ai-search-backend 2>/dev/null || true
sleep 2

echo "Step 2: Uploading snapshot to Qdrant..."
# Upload snapshot to Qdrant for recovery
curl -X POST \
    "http://localhost:6333/collections/$COLLECTION_NAME/snapshots/upload" \
    -H "Content-Type: multipart/form-data" \
    -F "snapshot=@$SNAPSHOT_PATH"

if [ $? -eq 0 ]; then
    echo "✓ Snapshot uploaded successfully"
else
    echo "ERROR: Failed to upload snapshot"
    npx pm2 start ai-search-backend 2>/dev/null || true
    exit 1
fi

echo ""
echo "Step 3: Recovering collection from snapshot..."
# Wait for recovery to complete
sleep 5

# Verify collection
COLLECTION_INFO=$(curl -s http://localhost:6333/collections/$COLLECTION_NAME)
POINTS_COUNT=$(echo "$COLLECTION_INFO" | jq -r '.result.points_count // 0')

echo "Collection restored with $POINTS_COUNT points"
echo ""

echo "Step 4: Restarting backend..."
npx pm2 start ai-search-backend 2>/dev/null || true
sleep 3

# Clean up
if [ "$LOCAL_SNAPSHOT" != "$SNAPSHOT_PATH" ]; then
    rm -f "$LOCAL_SNAPSHOT"
fi

echo ""
echo "=========================================="
echo "  RESTORE COMPLETED SUCCESSFULLY"
echo "  Points restored: $POINTS_COUNT"
echo "  $(date)"
echo "=========================================="

# Log restore to file
echo "$(date '+%Y-%m-%d %H:%M:%S') - Restore completed ($POINTS_COUNT points)" >> /opt/ai-search/logs/backup.log
