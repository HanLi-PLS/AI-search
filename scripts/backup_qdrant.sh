#!/bin/bash
# Qdrant backup script - Creates snapshots and uploads to S3
# Run this script weekly or before major changes

set -e

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/tmp/qdrant_backups"
COLLECTION_NAME="documents"

# Load S3 bucket from config
S3_BUCKET=$(grep "AWS_S3_BUCKET=" /opt/ai-search/.env 2>/dev/null | cut -d'=' -f2)

echo "=========================================="
echo "  QDRANT BACKUP STARTING"
echo "  $(date)"
echo "=========================================="
echo ""

# Check if Qdrant is running
if ! curl -s http://localhost:6333/collections >/dev/null 2>&1; then
    echo "ERROR: Qdrant is not accessible"
    exit 1
fi

# Create backup directory
mkdir -p "$BACKUP_DIR"

echo "Step 1: Creating Qdrant snapshot..."
# Create snapshot
SNAPSHOT_RESPONSE=$(curl -s -X POST http://localhost:6333/collections/$COLLECTION_NAME/snapshots)

if echo "$SNAPSHOT_RESPONSE" | grep -q "error"; then
    echo "ERROR: Failed to create snapshot"
    echo "$SNAPSHOT_RESPONSE"
    exit 1
fi

echo "Snapshot creation initiated. Waiting for completion..."
sleep 5

# Get latest snapshot name
SNAPSHOT_NAME=$(curl -s http://localhost:6333/collections/$COLLECTION_NAME/snapshots | jq -r '.result[-1].name')

if [ -z "$SNAPSHOT_NAME" ] || [ "$SNAPSHOT_NAME" = "null" ]; then
    echo "ERROR: Could not retrieve snapshot name"
    exit 1
fi

echo "Latest snapshot: $SNAPSHOT_NAME"
echo ""

echo "Step 2: Downloading snapshot..."
# Download snapshot
SNAPSHOT_FILE="${BACKUP_DIR}/qdrant_${COLLECTION_NAME}_${DATE}.snapshot"
curl -s -o "$SNAPSHOT_FILE" "http://localhost:6333/collections/$COLLECTION_NAME/snapshots/$SNAPSHOT_NAME"

if [ ! -f "$SNAPSHOT_FILE" ]; then
    echo "ERROR: Failed to download snapshot"
    exit 1
fi

SNAPSHOT_SIZE=$(du -h "$SNAPSHOT_FILE" | cut -f1)
echo "Snapshot downloaded: $SNAPSHOT_SIZE"
echo ""

# Upload to S3 if configured
if [ -n "$S3_BUCKET" ]; then
    echo "Step 3: Uploading to S3..."
    S3_PATH="s3://$S3_BUCKET/backups/qdrant/qdrant_${COLLECTION_NAME}_${DATE}.snapshot"

    aws s3 cp "$SNAPSHOT_FILE" "$S3_PATH" \
        --storage-class STANDARD_IA \
        --metadata "backup_date=$DATE,collection=$COLLECTION_NAME"

    if [ $? -eq 0 ]; then
        echo "✓ Backup uploaded to S3: $S3_PATH"

        # Clean up local snapshot after successful upload
        rm -f "$SNAPSHOT_FILE"
        echo "✓ Local snapshot cleaned up"
    else
        echo "ERROR: Failed to upload to S3"
        echo "Local snapshot preserved at: $SNAPSHOT_FILE"
        exit 1
    fi
else
    echo "Step 3: S3 not configured"
    echo "Local backup saved at: $SNAPSHOT_FILE"
fi

echo ""
echo "Step 4: Cleaning old backups (keeping last 4 weeks)..."

# Clean up old S3 backups (keep last 30 days)
if [ -n "$S3_BUCKET" ]; then
    CUTOFF_DATE=$(date -d "30 days ago" +%Y%m%d 2>/dev/null || date -v-30d +%Y%m%d)

    aws s3 ls s3://$S3_BUCKET/backups/qdrant/ | while read -r line; do
        FILE_DATE=$(echo $line | grep -oP 'qdrant_documents_\K[0-9]{8}')
        if [ -n "$FILE_DATE" ] && [ "$FILE_DATE" -lt "$CUTOFF_DATE" ]; then
            FILE_NAME=$(echo $line | awk '{print $4}')
            echo "Deleting old backup: $FILE_NAME"
            aws s3 rm "s3://$S3_BUCKET/backups/qdrant/$FILE_NAME"
        fi
    done
fi

# Clean up old local backups
find "$BACKUP_DIR" -name "qdrant_*.snapshot" -mtime +7 -delete 2>/dev/null || true

echo ""
echo "=========================================="
echo "  BACKUP COMPLETED SUCCESSFULLY"
echo "  Backup size: $SNAPSHOT_SIZE"
echo "  $(date)"
echo "=========================================="

# Log backup to file
echo "$(date '+%Y-%m-%d %H:%M:%S') - Backup completed successfully ($SNAPSHOT_SIZE)" >> /opt/ai-search/logs/backup.log
