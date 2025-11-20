#!/bin/bash
#
# Setup Script for Docker Cleanup Cron Job
# Installs a weekly cron job to clean up old Docker images
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLEANUP_SCRIPT="$SCRIPT_DIR/cleanup_docker.sh"

echo "Setting up Docker cleanup cron job..."

# Make cleanup script executable
chmod +x "$CLEANUP_SCRIPT"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "cleanup_docker.sh"; then
    echo "Docker cleanup cron job already exists. Skipping..."
    exit 0
fi

# Add weekly cron job (every Sunday at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * 0 $CLEANUP_SCRIPT >> /var/log/docker-cleanup.log 2>&1") | crontab -

echo "Docker cleanup cron job installed successfully!"
echo "Schedule: Every Sunday at 2:00 AM"
echo "Log file: /var/log/docker-cleanup.log"
echo ""
echo "To view current cron jobs, run: crontab -l"
echo "To manually run cleanup now, run: $CLEANUP_SCRIPT"
