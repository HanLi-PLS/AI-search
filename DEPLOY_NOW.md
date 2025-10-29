# Deploy to EC2 - Quick Guide

## Prerequisites Checklist

Before deploying, make sure you have:

- [ ] AWS Account access
- [ ] EC2 instance running (Amazon Linux 2023 or Ubuntu 22.04)
- [ ] SSH key (.pem file) to access EC2
- [ ] OpenAI API key stored in AWS Secrets Manager as `openai-api-key`
- [ ] S3 bucket `plfs-han-ai-search` exists
- [ ] IAM role attached to EC2 with permissions for Secrets Manager and S3

---

## Option 1: Create New EC2 Instance

### Step 1: Launch EC2 Instance

Go to AWS Console → EC2 → Launch Instance

**Settings:**
```
Name: ai-search-prod
AMI: Amazon Linux 2023 (or Ubuntu 22.04)
Instance Type: t3.medium (minimum) or t3.large (recommended)
Key pair: Create new or use existing
Storage: 50 GB gp3
```

**Security Group Rules:**
```
Type            Port    Source          Description
SSH             22      My IP           SSH access
Custom TCP      8000    0.0.0.0/0       Application
HTTP            80      0.0.0.0/0       Nginx (optional)
HTTPS           443     0.0.0.0/0       SSL (optional)
```

### Step 2: Create IAM Role

1. Go to IAM → Roles → Create Role
2. Select "AWS Service" → "EC2"
3. Create policy with this JSON:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "arn:aws:secretsmanager:us-west-2:*:secret:openai-api-key-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::plfs-han-ai-search",
        "arn:aws:s3:::plfs-han-ai-search/*"
      ]
    }
  ]
}
```

4. Name the role: `ai-search-role`
5. Attach role to EC2 instance: EC2 Console → Select instance → Actions → Security → Modify IAM role

---

## Option 2: Deploy to Existing EC2 Instance

### Step 1: Connect to EC2

```bash
# Make key secure
chmod 400 your-key.pem

# Connect to instance
ssh -i your-key.pem ec2-user@YOUR-EC2-PUBLIC-IP

# Or for Ubuntu:
ssh -i your-key.pem ubuntu@YOUR-EC2-PUBLIC-IP
```

### Step 2: Run Automated Setup

**Copy and paste this entire command block:**

```bash
# Download setup script
wget https://raw.githubusercontent.com/HanLi-PLS/AI-search/claude/ai-search-tool-011CUMmPzfCZLdSZBjHwvmT8/scripts/setup_ec2.sh

# Make executable
chmod +x setup_ec2.sh

# Run setup
sudo ./setup_ec2.sh
```

**When prompted:**
- Use AWS Secrets Manager? → **y** (yes)
- Use S3 for file storage? → **y** (yes)

**Wait 3-5 minutes for setup to complete.**

### Step 3: Verify Deployment

```bash
# Check services are running
sudo docker-compose ps

# Should show:
# ai-search-backend     Up
# ai-search-qdrant      Up

# View logs
sudo docker-compose logs -f

# Press Ctrl+C to stop viewing logs
```

### Step 4: Get Your Website URL

```bash
# Get public IP
curl http://checkip.amazonaws.com
```

Your application is now accessible at:
- **Web Interface**: `http://YOUR-PUBLIC-IP:8000`
- **API Docs**: `http://YOUR-PUBLIC-IP:8000/docs`
- **Qdrant Dashboard**: `http://YOUR-PUBLIC-IP:6333/dashboard`

---

## Testing Your Deployment

### Test 1: Access Web Interface

1. Open browser: `http://YOUR-PUBLIC-IP:8000`
2. You should see the AI Document Search interface

### Test 2: Upload a Test File

1. Create a simple test file on your computer:
   ```bash
   echo "This is a test document for AI search." > test.txt
   ```

2. Upload via web interface:
   - Click "Drag & drop files" or browse
   - Select `test.txt`
   - Wait for processing

3. Verify upload:
   - Should see "File uploaded successfully (stored in S3: ...)"
   - File appears in "Uploaded Documents" section

### Test 3: Search

1. Enter query: "test document"
2. Click Search
3. Should see your uploaded file in results

### Test 4: Verify S3 Storage

From your EC2 instance:
```bash
# List files in S3
aws s3 ls s3://plfs-han-ai-search/uploads/

# Should show your uploaded file
```

### Test 5: Run Integration Tests

From EC2 instance:
```bash
cd /opt/ai-search

# Test AWS Secrets Manager
python tests/test_aws_secrets.py

# Test S3 Storage
python tests/test_s3_storage.py

# Both should show all green checkmarks ✅
```

---

## Troubleshooting

### Problem: Can't connect to EC2

**Check security group:**
```bash
# From AWS Console
EC2 → Security Groups → Check inbound rules
# Port 8000 should allow 0.0.0.0/0
```

### Problem: Services not starting

```bash
# Check logs
sudo docker-compose logs backend

# Common issues:
# - IAM role not attached → Attach role in EC2 console
# - Secret not found → Check secret exists in Secrets Manager
# - S3 access denied → Check IAM policy includes S3 permissions
```

### Problem: "Access Denied" errors

**Verify IAM role:**
```bash
# From EC2 instance
aws sts get-caller-identity

# Should show your account ID and role ARN
```

**Test Secrets Manager:**
```bash
aws secretsmanager get-secret-value \
    --secret-id openai-api-key \
    --region us-west-2

# Should show your secret (masked)
```

**Test S3:**
```bash
aws s3 ls s3://plfs-han-ai-search/

# Should list bucket contents
```

---

## Manual Deployment (If Automated Script Fails)

See detailed manual steps in [DEPLOYMENT_AWS.md](DEPLOYMENT_AWS.md)

---

## Next Steps After Deployment

1. ✅ Deploy application
2. ✅ Test file upload
3. ⏳ Set up Nginx reverse proxy (optional)
4. ⏳ Configure SSL/HTTPS (optional)
5. ⏳ Set up CloudWatch monitoring (optional)
6. ⏳ Configure automatic backups

---

## Quick Commands Reference

```bash
# View logs
cd /opt/ai-search && sudo docker-compose logs -f

# Restart services
cd /opt/ai-search && sudo docker-compose restart

# Stop services
cd /opt/ai-search && sudo docker-compose down

# Update application
cd /opt/ai-search
git pull
sudo docker-compose up -d --build

# Check service status
sudo docker-compose ps

# Check disk space
df -h

# Check memory
free -m
```

---

## Support

If you encounter issues:
1. Check logs: `sudo docker-compose logs backend`
2. Verify IAM role and permissions
3. Run test scripts to verify AWS integrations
4. Check [SETUP_TESTING_GUIDE.md](SETUP_TESTING_GUIDE.md) for detailed troubleshooting

---

**Ready to deploy? Follow the steps above!** 🚀
