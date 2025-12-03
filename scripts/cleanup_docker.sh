#!/bin/bash
#
# Docker Cleanup Script
# Removes unused Docker images, containers, and volumes older than 30 days
# Recommended to run weekly via cron
#

echo "Starting Docker cleanup..."
echo "Date: $(date)"

# Remove unused Docker resources older than 30 days (720 hours)
docker system prune -af --volumes --filter "until=720h"

echo "Docker cleanup completed!"
echo "Current disk usage:"
df -h /

echo ""
echo "Remaining Docker images:"
docker images
