#!/bin/bash
# Setup script for AI Search optimizations
# This script sets up monitoring, backups, and Qdrant optimization

set -e

echo "=========================================="
echo "  AI SEARCH OPTIMIZATION SETUP"
echo "  $(date)"
echo "=========================================="
echo ""

# Check if running on EC2
if [ ! -d "/opt/ai-search" ]; then
    echo "ERROR: /opt/ai-search directory not found"
    echo "This script should be run on the EC2 instance"
    exit 1
fi

cd /opt/ai-search

echo "Step 1: Creating directories..."
mkdir -p logs
mkdir -p backups
mkdir -p tmp

echo "Step 2: Setting up scripts..."
# Make all scripts executable
chmod +x scripts/*.sh

echo "Step 3: Installing dependencies..."
# Install jq if not present
if ! command -v jq &> /dev/null; then
    echo "Installing jq..."
    sudo yum install -y jq || sudo apt-get install -y jq
fi

echo ""
echo "Step 4: Configuring Qdrant with optimizations..."

# Stop Qdrant container
echo "Stopping Qdrant container..."
docker stop ai-search-qdrant 2>/dev/null || true
sleep 2

# Copy Qdrant config
if [ -f qdrant-config.yaml ]; then
    echo "✓ Qdrant config file found"
else
    echo "ERROR: qdrant-config.yaml not found"
    exit 1
fi

# Restart Qdrant with new config
echo "Starting Qdrant with optimized configuration..."
docker rm ai-search-qdrant 2>/dev/null || true

docker run -d \
    --name ai-search-qdrant \
    -p 6333:6333 \
    -p 6334:6334 \
    -v $(pwd)/qdrant-config.yaml:/qdrant/config/production.yaml \
    -v qdrant_storage:/qdrant/storage \
    --restart unless-stopped \
    qdrant/qdrant:latest

echo "Waiting for Qdrant to start..."
sleep 10

# Verify Qdrant is running
if curl -s http://localhost:6333/collections >/dev/null 2>&1; then
    echo "✓ Qdrant is running with optimized configuration"
else
    echo "ERROR: Qdrant failed to start"
    exit 1
fi

echo ""
echo "Step 5: Setting up automated backups..."

# Create cron job for weekly backups (every Sunday at 2 AM)
CRON_CMD="0 2 * * 0 /opt/ai-search/scripts/backup_qdrant.sh >> /opt/ai-search/logs/backup.log 2>&1"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "backup_qdrant.sh"; then
    echo "✓ Backup cron job already exists"
else
    # Add cron job
    (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
    echo "✓ Added weekly backup cron job (Sundays at 2 AM)"
fi

echo ""
echo "Step 6: Restarting backend..."
npx pm2 restart ai-search-backend
sleep 5

# Check backend status
if npx pm2 list | grep -q "ai-search-backend.*online"; then
    echo "✓ Backend restarted successfully"
else
    echo "WARNING: Backend may not be running properly"
fi

echo ""
echo "Step 7: Running initial storage check..."
bash scripts/check_storage.sh

echo ""
echo "=========================================="
echo "  SETUP COMPLETED SUCCESSFULLY"
echo "=========================================="
echo ""
echo "Available commands:"
echo "  - Monitor storage:  bash scripts/check_storage.sh"
echo "  - Create backup:    bash scripts/backup_qdrant.sh"
echo "  - Restore backup:   bash scripts/restore_qdrant.sh <snapshot_path>"
echo ""
echo "Automated backups scheduled:"
echo "  - Weekly on Sundays at 2 AM"
echo "  - Logs: /opt/ai-search/logs/backup.log"
echo ""
echo "Optimizations enabled:"
echo "  ✓ Qdrant on-disk payload (scalable storage)"
echo "  ✓ Performance tuning for large collections"
echo "  ✓ Automated backup to S3"
echo "  ✓ Storage monitoring scripts"
echo ""
