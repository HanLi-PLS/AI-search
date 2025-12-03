# EC2 Resource Monitoring Guide

## Quick Resource Check

Run this script on your EC2 instance to check all resources:

```bash
bash /opt/ai-search/scripts/check_resources.sh
```

This will show:
1. Memory (RAM) usage and availability
2. Disk space usage
3. CPU cores and load average
4. PM2 process status and resource usage
5. Top memory-consuming processes
6. Application storage sizes (uploads, database, logs)
7. Active network ports
8. Docker status (if applicable)
9. System information
10. Resource analysis with warnings and recommendations

---

## When to Upgrade Resources

### Memory (RAM)

| Usage | Status | Action |
|-------|--------|--------|
| < 70% | ✅ Healthy | No action needed |
| 70-85% | ⚠️ Warning | Monitor closely, consider upgrade soon |
| > 85% | 🔴 Critical | Upgrade immediately |

**Signs you need more RAM:**
- Backend process crashes with "Out of Memory" errors
- Slow response times during peak usage
- Frequent process restarts in PM2
- System becoming unresponsive

### Disk Space

| Usage | Status | Action |
|-------|--------|--------|
| < 70% | ✅ Healthy | No action needed |
| 70-85% | ⚠️ Warning | Clean up or expand disk |
| > 85% | 🔴 Critical | Expand disk immediately |

**What consumes disk:**
- Uploaded documents (`/opt/ai-search/uploads`)
- Qdrant vector database (`/opt/ai-search/data/qdrant`)
- Application logs (`/opt/ai-search/logs`)
- SQLite databases (search job tracker, etc.)

**How to clean up:**
```bash
# Check what's using space
du -sh /opt/ai-search/* | sort -h

# Clean old PM2 logs
pm2 flush

# Clean old backup files (if any)
find /opt/ai-search -name "*.bak" -type f -mtime +30 -delete

# Rotate/archive large log files
cd /opt/ai-search/logs
gzip backend-out.log backend-error.log
```

### CPU & Load Average

| Load vs Cores | Status | Action |
|---------------|--------|--------|
| Load < Cores | ✅ Healthy | No action needed |
| Load = Cores | ⚠️ Warning | Monitor closely |
| Load > Cores | 🔴 Critical | Upgrade CPU or optimize code |

**Example:**
- 4 CPU cores, load average 2.5 → Healthy
- 4 CPU cores, load average 4.0 → At capacity
- 4 CPU cores, load average 8.0 → Overloaded

---

## Current Setup Analysis

Based on your earlier system check, you have:
- **RAM**: ~13GB total (~12GB available) ✅ Healthy
- **Disk**: 30GB (1% used) ✅ Healthy
- **CPU**: 16 cores (load avg 0.00) ✅ Very healthy

**Assessment**: Your current resources are **more than sufficient** for current usage.

---

## Recommended EC2 Instance Sizes

Based on concurrent users:

### Light Usage (1-5 concurrent users)
- **Instance**: t3.medium or t3a.medium
- **Specs**: 2 vCPU, 4GB RAM
- **Cost**: ~$30/month

### Medium Usage (5-20 concurrent users) ← **Your likely current setup**
- **Instance**: t3.large or t3a.large
- **Specs**: 2 vCPU, 8GB RAM
- **Cost**: ~$60/month

### Heavy Usage (20-50 concurrent users)
- **Instance**: t3.xlarge or t3a.xlarge
- **Specs**: 4 vCPU, 16GB RAM
- **Cost**: ~$120/month

### Very Heavy Usage (50+ concurrent users)
- **Instance**: t3.2xlarge or t3a.2xlarge
- **Specs**: 8 vCPU, 32GB RAM
- **Cost**: ~$240/month

---

## Monitoring Best Practices

### 1. Set up CloudWatch Alarms

Monitor these metrics:
- CPU Utilization > 80% for 5 minutes
- Memory Utilization > 85% for 5 minutes
- Disk Usage > 80%
- Status Check Failures

### 2. Regular Health Checks

Run the resource check script weekly:
```bash
bash /opt/ai-search/scripts/check_resources.sh | tee /tmp/resource-check-$(date +%Y%m%d).log
```

### 3. PM2 Monitoring

Check process health:
```bash
pm2 status
pm2 monit  # Real-time monitoring
pm2 logs --lines 100  # Check for errors
```

### 4. Database Size Monitoring

Check vector database growth:
```bash
du -sh /opt/ai-search/data/qdrant
# If > 10GB, consider cleanup or expansion
```

---

## Optimization Tips

### If Memory is High:
1. Restart PM2 processes occasionally to clear memory leaks:
   ```bash
   pm2 restart all
   ```
2. Limit concurrent file processing:
   - Adjust `MAX_CONCURRENT_VISION_CALLS` in .env (default: 10)
3. Review and close inactive user sessions

### If Disk is High:
1. Implement S3 storage for uploads (already configured if `USE_S3_STORAGE=true`)
2. Archive old documents
3. Rotate logs regularly
4. Clean up temporary files

### If CPU is High:
1. Optimize search queries
2. Add caching for frequent searches
3. Limit concurrent searches per user
4. Upgrade to larger instance

---

## Current Resource Usage Baseline

Run this command and save the output as your baseline:
```bash
bash /opt/ai-search/scripts/check_resources.sh > /opt/ai-search/logs/baseline-$(date +%Y%m%d).log
```

Compare future checks against this baseline to identify trends.

---

## Emergency Actions

### If System Becomes Unresponsive:

1. **Check memory:**
   ```bash
   free -h
   ```

2. **Kill memory-hungry processes if needed:**
   ```bash
   ps aux --sort=-%mem | head -20
   # If a process is using too much memory:
   kill -9 <PID>
   ```

3. **Restart PM2:**
   ```bash
   pm2 restart all
   ```

4. **Check disk space:**
   ```bash
   df -h
   # If disk is full, clean up:
   pm2 flush
   find /opt/ai-search/logs -name "*.log" -mtime +7 -delete
   ```

5. **Reboot EC2 instance (last resort):**
   ```bash
   sudo reboot
   ```

---

## Contact AWS Support

If you consistently hit resource limits, contact AWS support to:
1. Upgrade instance type
2. Increase EBS volume size
3. Set up auto-scaling (for traffic spikes)
4. Implement load balancing (for multiple instances)
