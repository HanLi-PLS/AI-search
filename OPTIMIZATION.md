# AI Search Optimization Guide

This document describes the storage optimizations and management tools for the AI Search application.

## Storage Architecture

### Vector Database (Qdrant)
- **Location**: Docker volume (`qdrant_storage`)
- **Storage**: ~113 MB per 1000 files (with 768-dim embeddings)
- **Optimizations**: On-disk payload, performance tuning

### Original Files
- **Location**: AWS S3 bucket (`plfs-han-ai-search`)
- **Storage**: Varies by file size
- **Cleanup**: Local files deleted after S3 upload

### Embeddings Model
- **Current**: Alibaba-NLP/gte-multilingual-base
- **Dimensions**: 768
- **Speed**: ~2-3 minutes per file
- **Batch**: Parallel processing in zip uploads

## Storage Estimates

| Files | Qdrant Storage | S3 Storage | Total | Upload Time (zip) |
|-------|----------------|------------|-------|-------------------|
| 100   | ~11 MB         | ~49 MB     | ~60 MB| ~10-15 min        |
| 500   | ~57 MB         | ~244 MB    | ~301 MB| ~30-45 min       |
| 1000  | ~113 MB        | ~488 MB    | ~601 MB| ~60-90 min       |

## Setup Instructions

### 1. Deploy Optimizations

On your EC2 instance:

```bash
cd /opt/ai-search

# Pull latest code with optimization scripts
git pull origin claude/evaluate-html-to-react-011CUyQ9hSAQupSJFsteh1nb

# Run setup script
bash scripts/setup_optimizations.sh
```

This will:
- Configure Qdrant with on-disk storage
- Set up automated weekly backups
- Install monitoring scripts
- Restart services with new configuration

### 2. Manual Commands

#### Monitor Storage
```bash
bash scripts/check_storage.sh
```

Shows:
- Qdrant database size
- Collection statistics (vectors, points)
- S3 bucket usage
- EC2 disk space
- Memory usage
- Recent activity

#### Create Backup
```bash
bash scripts/backup_qdrant.sh
```

Creates snapshot and uploads to S3:
- Location: `s3://plfs-han-ai-search/backups/qdrant/`
- Retention: 30 days (automatic cleanup)
- Local cleanup: After successful S3 upload

#### Restore Backup
```bash
# From S3
bash scripts/restore_qdrant.sh s3://plfs-han-ai-search/backups/qdrant/qdrant_documents_20250111_120000.snapshot

# From local file
bash scripts/restore_qdrant.sh /tmp/backup.snapshot

# List available backups
bash scripts/restore_qdrant.sh
```

## Qdrant Configuration

The `qdrant-config.yaml` file includes:

### On-Disk Payload
```yaml
storage:
  on_disk_payload: true
```
- Stores text content on disk instead of RAM
- Enables scaling to 10,000+ files
- Slight performance trade-off for scalability

### Performance Tuning
```yaml
service:
  max_search_threads: 4

storage:
  performance:
    max_segment_size_kb: 100000
```
- Optimized for t3.xlarge (4 vCPUs)
- Large segment size for bulk operations

### Optional: Quantization
```yaml
# Uncomment to enable (4x memory reduction)
quantization:
  scalar:
    type: int8
    quantile: 0.99
    always_ram: false
```
- Reduces vector memory by 4x
- Minimal accuracy loss (~1-2%)
- Enable when RAM becomes limiting factor

## Automated Backups

### Schedule
- **Frequency**: Weekly (Sundays at 2 AM)
- **Location**: S3 Standard-IA storage class
- **Retention**: 30 days (automatic cleanup)

### Cron Job
```bash
# View current cron jobs
crontab -l

# Edit cron jobs
crontab -e
```

### Backup Logs
```bash
tail -f /opt/ai-search/logs/backup.log
```

## Bulk Upload Best Practices

### Use Zip Files for Multiple Documents

**Benefits:**
- Parallel processing (all files at once)
- Chinese filename support (proper encoding)
- Automatic cleanup of temp files

**Example:**
```bash
# Create zip with multiple files
zip -r documents.zip *.pdf *.docx

# Upload via web interface
# All files process in parallel
```

**Performance:**
- 100 files: ~10-15 minutes (vs 200-300 minutes sequential)
- Files process simultaneously
- Shared embedding model initialization

### File Organization

**Recommended structure:**
```
project_name/
  ├── background/
  │   ├── company_overview.pdf
  │   └── market_analysis.docx
  ├── financials/
  │   ├── income_statement.xlsx
  │   └── balance_sheet.xlsx
  └── reports/
      ├── q1_report.pdf
      └── q2_report.pdf
```

Zip entire project:
```bash
zip -r project_name.zip project_name/
```

## Monitoring and Maintenance

### Daily Monitoring
```bash
# Check storage and health
bash scripts/check_storage.sh

# View recent logs
npx pm2 logs ai-search-backend --lines 50
```

### Weekly Maintenance
- Automatic backup runs Sunday 2 AM
- Old backups cleaned up (>30 days)
- Review backup logs

### Monthly Review
- Check S3 costs (backups + uploads)
- Review Qdrant collection size
- Consider quantization if RAM usage high

## Troubleshooting

### Qdrant Not Accessible
```bash
# Check container status
docker ps | grep qdrant

# Restart container
docker restart ai-search-qdrant

# Check logs
docker logs ai-search-qdrant --tail 50
```

### Backup Failed
```bash
# Check backup logs
cat /opt/ai-search/logs/backup.log

# Manually create backup
bash scripts/backup_qdrant.sh

# Check S3 permissions
aws s3 ls s3://plfs-han-ai-search/backups/
```

### High Memory Usage
```bash
# Check current usage
free -h

# Enable quantization in qdrant-config.yaml
# Uncomment the quantization section

# Restart Qdrant
docker restart ai-search-qdrant
```

### Slow Embedding Generation
- Already using Alibaba-NLP model (optimized)
- Consider GPU instance for 100+ files regularly
- Use zip uploads for parallel processing

## Cost Optimization

### S3 Storage
- **Uploads**: Standard storage class
- **Backups**: Standard-IA (cheaper for infrequent access)
- **Lifecycle**: 30-day retention

### EC2 Instance
- **Current**: t3.xlarge (16GB RAM)
- **Sufficient for**: 1000+ files
- **Upgrade to GPU**: Only if processing >100 files daily

## Future Scaling

### When to Upgrade

**Upgrade to GPU instance (g4dn.xlarge) if:**
- Processing >100 files daily
- Need faster embedding generation
- Can tolerate higher costs

**Upgrade Qdrant storage if:**
- Collection size >10,000 files
- Qdrant storage >50GB
- Consider dedicated Qdrant EBS volume

**Enable quantization if:**
- RAM usage >12GB consistently
- Need to store 5000+ files
- Can accept 1-2% accuracy loss
