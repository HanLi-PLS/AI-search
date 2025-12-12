#!/bin/bash
# Resource check script for AI-search EC2 instance
# Run this on your EC2 instance: bash /opt/ai-search/scripts/check_resources.sh

echo "=================================="
echo "AI-SEARCH EC2 RESOURCE CHECK"
echo "=================================="
echo ""

# 1. Memory (RAM)
echo "=== 1. MEMORY (RAM) ==="
free -h
USED_MEM=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100}')
echo "Memory Usage: ${USED_MEM}%"
echo ""

# 2. Disk Space
echo "=== 2. DISK SPACE ==="
df -h /
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
echo "Root Disk Usage: ${DISK_USAGE}%"
echo ""

# 3. CPU & System Load
echo "=== 3. CPU & LOAD AVERAGE ==="
echo "CPU Cores: $(nproc)"
uptime
LOAD_1MIN=$(uptime | awk -F'load average:' '{print $2}' | awk -F',' '{print $1}' | xargs)
echo "1-min Load Average: ${LOAD_1MIN}"
echo ""

# 4. PM2 Processes
echo "=== 4. PM2 PROCESSES ==="
if command -v pm2 &> /dev/null; then
    pm2 list
    echo ""
    pm2 describe ai-search-backend 2>/dev/null | grep -E "status|memory|cpu|uptime|restarts" || echo "Backend process info not available"
    echo ""
    pm2 describe ai-search-frontend 2>/dev/null | grep -E "status|memory|cpu|uptime|restarts" || echo "Frontend process info not available"
else
    echo "PM2 not installed or not in PATH"
fi
echo ""

# 5. Top Memory Consuming Processes
echo "=== 5. TOP MEMORY CONSUMERS ==="
ps aux --sort=-%mem | head -11
echo ""

# 6. Application Storage
echo "=== 6. APPLICATION STORAGE ==="
if [ -d "/opt/ai-search" ]; then
    echo "Total app size:"
    du -sh /opt/ai-search 2>/dev/null || echo "Cannot read /opt/ai-search"
    echo ""

    echo "Uploads directory:"
    du -sh /opt/ai-search/uploads 2>/dev/null || echo "No uploads directory"

    echo "Qdrant database:"
    du -sh /opt/ai-search/data/qdrant 2>/dev/null || echo "No qdrant data"

    echo "SQLite databases:"
    find /opt/ai-search -name "*.db" -exec du -h {} \; 2>/dev/null | head -10

    echo "Logs:"
    du -sh /opt/ai-search/logs 2>/dev/null || echo "No logs directory"
else
    echo "/opt/ai-search not found"
fi
echo ""

# 7. Network & Port Usage
echo "=== 7. ACTIVE PORTS ==="
if command -v netstat &> /dev/null; then
    netstat -tuln | grep -E "8000|5173|6333" || echo "Key ports not listening"
else
    ss -tuln | grep -E "8000|5173|6333" || echo "Key ports not listening (using ss)"
fi
echo ""

# 8. Docker (if using docker-compose)
echo "=== 8. DOCKER STATUS ==="
if command -v docker &> /dev/null; then
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "Docker not running or no containers"
    echo ""
    docker stats --no-stream 2>/dev/null || echo "Cannot get docker stats"
else
    echo "Docker not installed"
fi
echo ""

# 9. System Info
echo "=== 9. SYSTEM INFO ==="
echo "OS: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)"
echo "Kernel: $(uname -r)"
echo "Architecture: $(uname -m)"
echo "Uptime: $(uptime -p)"
echo ""

# 10. Resource Recommendations
echo "=== 10. RESOURCE ANALYSIS ==="
echo ""

# Memory Check
if (( $(echo "$USED_MEM > 80" | bc -l) )); then
    echo "⚠️  WARNING: Memory usage is HIGH (${USED_MEM}%)"
    echo "   Consider upgrading RAM or optimizing memory usage"
else
    echo "✅ Memory usage is healthy (${USED_MEM}%)"
fi

# Disk Check
if [ "$DISK_USAGE" -gt 80 ]; then
    echo "⚠️  WARNING: Disk usage is HIGH (${DISK_USAGE}%)"
    echo "   Consider cleaning up old files or expanding disk"
else
    echo "✅ Disk usage is healthy (${DISK_USAGE}%)"
fi

# Load Average Check (for systems with more than 1 CPU)
NCPUS=$(nproc)
if (( $(echo "$LOAD_1MIN > $NCPUS" | bc -l) )); then
    echo "⚠️  WARNING: Load average is HIGH (${LOAD_1MIN} on ${NCPUS} CPUs)"
    echo "   System may be overloaded"
else
    echo "✅ Load average is healthy (${LOAD_1MIN} on ${NCPUS} CPUs)"
fi

echo ""
echo "=== RECOMMENDED EC2 INSTANCE SIZES ==="
echo ""
echo "Current estimated requirements:"
echo "- Light usage (1-5 users): t3.medium (2 vCPU, 4GB RAM)"
echo "- Medium usage (5-20 users): t3.large (2 vCPU, 8GB RAM) ← Your current setup"
echo "- Heavy usage (20-50 users): t3.xlarge (4 vCPU, 16GB RAM)"
echo "- Very heavy (50+ users): t3.2xlarge (8 vCPU, 32GB RAM)"
echo ""

echo "=================================="
echo "RESOURCE CHECK COMPLETE"
echo "=================================="
