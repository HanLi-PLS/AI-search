# Deployment Scripts

This directory contains deployment scripts and configuration files for the AI-Search stock tracker.

## Crontab - Automated Data Updates

### Overview

The application fetches historical stock price data from CapIQ and stores it in the database. To keep this data fresh, we use cron jobs to automatically update the data on a schedule.

### Schedule

- **Daily Update** (Monday-Friday, 9:00 AM UTC / 5:00 PM HKT)
  - Fetches last 5 days of data after HK market close
  - Ensures we always have the latest prices
  - Runs only on weekdays when markets are open

- **Weekly Full Refresh** (Sunday, 2:00 AM UTC / 10:00 AM HKT)
  - Fetches 90 days of data to backfill any gaps
  - Ensures data consistency over weekends/holidays
  - Runs once a week

### Installation

#### Quick Install

```bash
cd /opt/ai-search
./deployment/install-crontab.sh
```

The script will:
1. Show you what will be installed
2. Ask for confirmation
3. Backup your existing crontab (if any)
4. Install the new cron jobs

#### Manual Install

If you prefer to install manually:

```bash
cd /opt/ai-search
crontab deployment/crontab
```

### Verify Installation

Check that cron jobs are installed:

```bash
crontab -l
```

### Logs

Cron job output is logged to:
- `/opt/ai-search/logs/capiq-update.log` - Daily updates
- `/opt/ai-search/logs/capiq-update-weekly.log` - Weekly full refresh

To monitor logs:

```bash
# Daily update log
tail -f /opt/ai-search/logs/capiq-update.log

# Weekly update log
tail -f /opt/ai-search/logs/capiq-update-weekly.log
```

### Uninstall

To remove all cron jobs:

```bash
crontab -r
```

To restore from backup:

```bash
crontab deployment/crontab.backup.YYYYMMDD_HHMMSS
```

### Troubleshooting

**Cron jobs not running?**

1. Check if cron service is running:
   ```bash
   systemctl status cron
   # or
   systemctl status crond
   ```

2. Check cron logs:
   ```bash
   grep CRON /var/log/syslog
   # or
   journalctl -u cron
   ```

3. Verify the backend API is running:
   ```bash
   curl http://localhost:8000/health
   ```

**Manual test:**

Run the update manually to test:

```bash
curl -X POST "http://localhost:8000/api/stocks/update-capiq-history?days=5"
```

### Customization

To customize the schedule, edit `deployment/crontab` and run the install script again.

Cron schedule format:
```
* * * * *
│ │ │ │ │
│ │ │ │ └─── Day of week (0-6, Sunday=0)
│ │ │ └───── Month (1-12)
│ │ └─────── Day of month (1-31)
│ └───────── Hour (0-23)
└─────────── Minute (0-59)
```

Examples:
- `0 9 * * 1-5` - 9:00 AM UTC, Monday-Friday
- `*/30 * * * *` - Every 30 minutes
- `0 2 * * 0` - 2:00 AM UTC, Sunday only
