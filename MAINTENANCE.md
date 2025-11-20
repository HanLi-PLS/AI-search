# Server Maintenance Guide

This guide covers routine maintenance tasks for the AI Search application.

## Automated Cleanup

### Docker Cleanup (Weekly)

Docker images can accumulate over time and consume significant disk space. We provide automated cleanup scripts.

**Setup (one-time):**

```bash
cd /opt/ai-search
./scripts/setup_docker_cleanup.sh
```

This installs a weekly cron job that:
- Runs every Sunday at 2:00 AM
- Removes Docker images/containers unused for 30+ days
- Logs output to `/var/log/docker-cleanup.log`

**Manual cleanup:**

```bash
# Run cleanup script manually
./scripts/cleanup_docker.sh

# Or use Docker directly (removes ALL unused images immediately)
docker system prune -a --volumes
```

**View cleanup logs:**

```bash
tail -f /var/log/docker-cleanup.log
```

**View/edit cron jobs:**

```bash
# List current cron jobs
crontab -l

# Edit cron jobs
crontab -e
```

## Disk Space Monitoring

**Check disk usage:**

```bash
df -h
```

**Find large directories:**

```bash
# Top 10 largest directories in /opt/ai-search
sudo du -sh /opt/ai-search/* | sort -hr | head -10

# Check Docker space usage
docker system df
```

**Common large directories:**

- `/opt/ai-search/venv` (~7GB) - Python virtual environment
- `/home/ec2-user/nltk_data` (~2.6GB) - NLTK language data
- `/var/lib/qdrant` - Vector database storage (grows with uploaded documents)
- Docker images - Old/unused images can accumulate

## Log Management

**PM2 logs:**

```bash
# Flush old logs
pm2 flush

# View logs
pm2 logs ai-search-backend --lines 100
pm2 logs ai-search-frontend --lines 100
```

**System logs:**

```bash
# Clean old journal logs (keep only 7 days)
sudo journalctl --vacuum-time=7d
```

## Database Maintenance

### Qdrant Vector Database

**Check Qdrant storage:**

```bash
sudo du -sh /var/lib/qdrant
```

**Clear all documents (CAUTION - irreversible):**

```bash
# Stop Qdrant
sudo systemctl stop qdrant

# Remove data
sudo rm -rf /var/lib/qdrant/storage/*

# Start Qdrant
sudo systemctl start qdrant
```

### SQLite Database (Stock Data)

**Location:** `/opt/ai-search/data/db/stocks.db`

**Backup:**

```bash
cp /opt/ai-search/data/db/stocks.db /opt/ai-search/backups/stocks_$(date +%Y%m%d).db
```

## Update Checklist

When deploying updates:

1. Pull latest code:
   ```bash
   cd /opt/ai-search
   git pull origin <branch-name>
   ```

2. Update backend dependencies (if requirements.txt changed):
   ```bash
   source venv/bin/activate
   pip install -r requirements.txt
   pm2 restart ai-search-backend
   ```

3. Update frontend (if frontend code changed):
   ```bash
   cd frontend
   npm run build
   pm2 restart ai-search-frontend
   ```

4. Check services are running:
   ```bash
   pm2 status
   ```

## Emergency Recovery

**If disk is full:**

1. Remove old Docker images: `docker system prune -a --volumes`
2. Clear PM2 logs: `pm2 flush`
3. Clear journal logs: `sudo journalctl --vacuum-time=1d`
4. Remove old NLTK data: See disk space section above

**If Qdrant fails with "No space left":**

Follow disk cleanup steps above, then restart Qdrant:
```bash
sudo systemctl restart qdrant
```

**If services won't start:**

```bash
# Check logs
pm2 logs ai-search-backend --err --lines 50

# Restart all services
pm2 restart all

# If still failing, check system resources
free -h
df -h
```
