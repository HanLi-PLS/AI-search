#!/bin/bash
#
# Install crontab for AI-Search stock tracker
#
# This script installs the scheduled tasks defined in deployment/crontab
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CRONTAB_FILE="$SCRIPT_DIR/crontab"

echo "=========================================="
echo "Installing AI-Search Crontab"
echo "=========================================="
echo ""

# Check if crontab file exists
if [ ! -f "$CRONTAB_FILE" ]; then
    echo "❌ Error: Crontab file not found at $CRONTAB_FILE"
    exit 1
fi

echo "📋 Crontab file found: $CRONTAB_FILE"
echo ""

# Show what will be installed
echo "The following scheduled tasks will be installed:"
echo ""
grep -v '^#' "$CRONTAB_FILE" | grep -v '^$' || echo "(no tasks found)"
echo ""

# Ask for confirmation
read -p "Install these cron jobs? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Installation cancelled"
    exit 1
fi

# Backup existing crontab
echo "💾 Backing up existing crontab..."
crontab -l > "$SCRIPT_DIR/crontab.backup.$(date +%Y%m%d_%H%M%S)" 2>/dev/null || echo "No existing crontab to backup"

# Install new crontab
echo "📦 Installing new crontab..."
crontab "$CRONTAB_FILE"

echo ""
echo "✅ Crontab installed successfully!"
echo ""
echo "To view installed cron jobs:"
echo "  crontab -l"
echo ""
echo "To remove cron jobs:"
echo "  crontab -r"
echo ""
echo "Logs will be written to:"
echo "  /opt/ai-search/logs/capiq-update.log (daily)"
echo "  /opt/ai-search/logs/capiq-update-weekly.log (weekly)"
echo ""
