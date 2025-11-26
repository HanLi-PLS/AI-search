#!/bin/bash
# Setup daily backend restart to clear cache and prevent Tushare fallback issues
# This ensures fresh CapIQ data is fetched daily

set -e

echo "Setting up daily backend restart at 3 AM..."

# Check if PM2 is installed
if ! command -v pm2 &> /dev/null; then
    echo "Error: PM2 not found. Please install PM2 first."
    exit 1
fi

# Backup existing crontab
BACKUP_DIR="/opt/ai-search/deployment"
BACKUP_FILE="${BACKUP_DIR}/crontab.backup.$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
crontab -l > "$BACKUP_FILE" 2>/dev/null || echo "No existing crontab to backup"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "pm2 restart ai-search-backend"; then
    echo "Daily restart cron job already exists:"
    crontab -l | grep "pm2 restart ai-search-backend"
    echo ""
    read -p "Do you want to update it? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping cron job setup."
        exit 0
    fi
    # Remove existing job
    crontab -l | grep -v "pm2 restart ai-search-backend" | crontab -
fi

# Add new cron job (restart at 3 AM daily)
(crontab -l 2>/dev/null; echo "0 3 * * * /usr/bin/pm2 restart ai-search-backend > /dev/null 2>&1") | crontab -

echo "✓ Daily restart configured successfully!"
echo ""
echo "Current crontab:"
crontab -l
echo ""
echo "The backend will restart daily at 3 AM to clear cache and ensure fresh CapIQ data."
echo "Backup saved to: $BACKUP_FILE"
