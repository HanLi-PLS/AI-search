#!/bin/bash
# Storage monitoring script for AI Search application
# This script checks Qdrant database size, collection statistics, and S3 usage

set -e

echo "=========================================="
echo "  AI SEARCH STORAGE MONITORING"
echo "  $(date)"
echo "=========================================="
echo ""

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo "Warning: jq not installed. Installing..."
    sudo yum install -y jq || sudo apt-get install -y jq
fi

# 1. Qdrant Docker Volume Storage
echo "=== Qdrant Vector Database Storage ==="
if docker ps | grep -q ai-search-qdrant; then
    QDRANT_SIZE=$(docker exec ai-search-qdrant du -sh /qdrant/storage 2>/dev/null | cut -f1 || echo "N/A")
    echo "Storage used: $QDRANT_SIZE"
else
    echo "Warning: Qdrant container not running"
fi
echo ""

# 2. Collection Statistics
echo "=== Collection Statistics ==="
COLLECTION_INFO=$(curl -s http://localhost:6333/collections/documents 2>/dev/null)
if [ $? -eq 0 ] && [ -n "$COLLECTION_INFO" ]; then
    echo "$COLLECTION_INFO" | jq -r '
        "Vectors count:    \(.result.vectors_count // 0 | tostring)",
        "Points count:     \(.result.points_count // 0 | tostring)",
        "Segments count:   \(.result.segments_count // 0 | tostring)",
        "Status:           \(.result.status // "unknown")"
    '

    echo ""
    echo "Payload fields tracked:"
    echo "$COLLECTION_INFO" | jq -r '.result.payload_schema | keys[]' | sed 's/^/  - /'
else
    echo "Warning: Could not retrieve collection info"
fi
echo ""

# 3. Embedding Model Info
echo "=== Embedding Model Configuration ==="
EMBEDDING_MODEL=$(grep "EMBEDDING_MODEL=" /opt/ai-search/.env 2>/dev/null | cut -d'=' -f2 || echo "Not configured")
echo "Current model: $EMBEDDING_MODEL"
echo ""

# 4. S3 Bucket Usage (if enabled)
echo "=== S3 Storage Usage ==="
USE_S3=$(grep "USE_S3_STORAGE=" /opt/ai-search/.env 2>/dev/null | cut -d'=' -f2 || echo "false")
S3_BUCKET=$(grep "AWS_S3_BUCKET=" /opt/ai-search/.env 2>/dev/null | cut -d'=' -f2)

if [ "$USE_S3" = "true" ] && [ -n "$S3_BUCKET" ]; then
    echo "S3 Bucket: $S3_BUCKET"
    aws s3 ls s3://$S3_BUCKET/uploads/ --recursive --human-readable --summarize 2>/dev/null | tail -2 || echo "Could not retrieve S3 stats"
else
    echo "S3 storage not enabled"
    echo "Local uploads directory:"
    du -sh /opt/ai-search/uploads 2>/dev/null || echo "N/A"
fi
echo ""

# 5. Disk Space
echo "=== EC2 Disk Space ==="
df -h / | grep -v Filesystem
echo ""

# 6. Memory Usage
echo "=== Memory Usage ==="
free -h | grep -E "Mem:|Swap:"
echo ""

# 7. Recent Upload Activity
echo "=== Recent Activity (Last 24 hours) ==="
if [ -f /opt/ai-search/logs/backend-out-0.log ]; then
    RECENT_UPLOADS=$(grep -c "File uploaded:" /opt/ai-search/logs/backend-out-0.log 2>/dev/null || echo "0")
    echo "Files uploaded: $RECENT_UPLOADS"
else
    echo "No log file found"
fi
echo ""

echo "=========================================="
echo "  Monitoring complete"
echo "=========================================="
