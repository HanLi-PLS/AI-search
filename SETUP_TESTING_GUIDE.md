# Complete Setup and Testing Guide

This guide walks you through setting up AWS Secrets Manager, S3 storage, and deploying to EC2.

## Table of Contents

1. [AWS Secrets Manager Setup](#1-aws-secrets-manager-setup)
2. [S3 Storage Setup](#2-s3-storage-setup)
3. [Testing AWS Integration](#3-testing-aws-integration)
4. [EC2 Deployment](#4-ec2-deployment)
5. [Verification](#5-verification)
6. [Troubleshooting](#6-troubleshooting)

---

## 1. AWS Secrets Manager Setup

### Step 1.1: Create the Secret

```bash
# Create OpenAI API key secret
aws secretsmanager create-secret \
    --name openai-api-key \
    --description "OpenAI API key for AI Document Search" \
    --secret-string '{"key":"YOUR-OPENAI-API-KEY-HERE"}' \
    --region us-west-2
```

### Step 1.2: Verify Secret

```bash
# Verify the secret was created
aws secretsmanager describe-secret \
    --secret-id openai-api-key \
    --region us-west-2

# Test retrieval (masks the value)
aws secretsmanager get-secret-value \
    --secret-id openai-api-key \
    --region us-west-2
```

### Step 1.3: Configure IAM Permissions

**For EC2 Instance** (recommended):

Create an IAM role with this policy:

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
    }
  ]
}
```

Attach this role to your EC2 instance.

**For Local Development**:

Configure AWS CLI:
```bash
aws configure
# Enter your AWS Access Key ID
# Enter your AWS Secret Access Key
# Default region: us-west-2
# Default output format: json
```

---

## 2. S3 Storage Setup

### Step 2.1: Create/Verify S3 Bucket

```bash
# Check if bucket exists
aws s3 ls s3://plfs-han-ai-search --region us-west-2

# If bucket doesn't exist, create it
aws s3 mb s3://plfs-han-ai-search --region us-west-2
```

### Step 2.2: Configure Bucket Permissions

Create an IAM policy for S3 access:

```json
{
  "Version": "2012-10-17",
  "Statement": [
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

### Step 2.3: Test S3 Access

```bash
# Upload a test file
echo "test" > test.txt
aws s3 cp test.txt s3://plfs-han-ai-search/test/ --region us-west-2

# Verify upload
aws s3 ls s3://plfs-han-ai-search/test/ --region us-west-2

# Clean up
aws s3 rm s3://plfs-han-ai-search/test/test.txt --region us-west-2
rm test.txt
```

---

## 3. Testing AWS Integration

### Step 3.1: Test AWS Secrets Manager

```bash
cd AI-search

# Run the Secrets Manager test
python tests/test_aws_secrets.py
```

**Expected Output:**
```
============================================================
AWS Secrets Manager Integration Test
============================================================
Testing AWS credentials...
✅ AWS credentials configured
   Account: 123456789012
   User ARN: arn:aws:iam::123456789012:user/your-user

Testing Secrets Manager access...
✅ Secrets Manager accessible

Listing available secrets...
   Found 1 secret(s):
   - openai-api-key

Testing OpenAI API key retrieval...
✅ OpenAI API key retrieved successfully
   Secret name: openai-api-key
   Region: us-west-2
   Key preview: sk-proj-abc123...

============================================================
Test Summary
============================================================
✅ PASS - AWS Credentials
✅ PASS - Secrets Manager Access
✅ PASS - List Secrets
✅ PASS - OpenAI Secret

============================================================
🎉 All tests passed! AWS Secrets Manager is configured correctly.
```

### Step 3.2: Test S3 Storage

```bash
# Run the S3 storage test
python tests/test_s3_storage.py
```

**Expected Output:**
```
============================================================
S3 Storage Integration Test
============================================================
Bucket: plfs-han-ai-search
Region: us-west-2
============================================================
Testing AWS credentials...
✅ AWS credentials configured

Testing S3 bucket access: plfs-han-ai-search...
✅ Bucket 'plfs-han-ai-search' exists and is accessible

Testing S3 bucket permissions...
   ✅ s3:ListBucket - OK

Testing S3 operations...
   Testing upload...
   ✅ Upload successful
   Testing file existence check...
   ✅ File exists
   Testing get file size...
   ✅ File size correct: 35 bytes
   Testing download...
   ✅ Download successful
   Testing list files...
   ✅ List files successful (1 file(s) found)
   Testing presigned URL generation...
   ✅ Presigned URL generated
   Testing delete...
   ✅ Delete successful
   Testing file no longer exists...
   ✅ File successfully deleted

✅ All S3 operations successful

============================================================
🎉 All tests passed! S3 storage is configured correctly.
```

---

## 4. EC2 Deployment

### Step 4.1: Launch EC2 Instance

**Instance Configuration:**
- **AMI**: Amazon Linux 2023 or Ubuntu 22.04 LTS
- **Instance Type**: t3.medium (minimum), t3.large (recommended)
- **Storage**: 50 GB gp3
- **Security Group**:
  - Port 22 (SSH) from your IP
  - Port 8000 (HTTP) from 0.0.0.0/0
  - Port 80 (HTTP) from 0.0.0.0/0 (optional, for Nginx)
  - Port 443 (HTTPS) from 0.0.0.0/0 (optional, for SSL)

**IAM Role**: Attach role with Secrets Manager and S3 permissions

### Step 4.2: Connect to EC2

```bash
# Make key secure
chmod 400 your-key.pem

# Connect
ssh -i your-key.pem ec2-user@<your-ec2-public-ip>
```

### Step 4.3: Run Automated Setup

**Option A: Download and run script directly**

```bash
# Download setup script
wget https://raw.githubusercontent.com/HanLi-PLS/AI-search/claude/ai-search-tool-011CUMmPzfCZLdSZBjHwvmT8/scripts/setup_ec2.sh

# Make executable
chmod +x setup_ec2.sh

# Run setup
sudo ./setup_ec2.sh
```

The script will:
1. Update system packages
2. Install Docker and Docker Compose
3. Install Git
4. Clone the repository
5. Configure environment variables
6. Start the services

**Follow the prompts:**
- Use AWS Secrets Manager? → **Yes**
- Use S3 for file storage? → **Yes**

**Option B: Manual setup**

See [DEPLOYMENT_AWS.md](DEPLOYMENT_AWS.md) for detailed manual steps.

### Step 4.4: Configure .env on EC2

```bash
cd /opt/ai-search
sudo nano .env
```

**Production Configuration:**
```env
# AWS Secrets Manager
USE_AWS_SECRETS=true
AWS_SECRET_NAME_OPENAI=openai-api-key
AWS_REGION=us-west-2

# S3 Storage
USE_S3_STORAGE=true
AWS_S3_BUCKET=plfs-han-ai-search
S3_UPLOAD_PREFIX=uploads/

# Vision Model
VISION_MODEL=o4-mini

# Qdrant (Docker)
QDRANT_HOST=qdrant
QDRANT_PORT=6333
```

### Step 4.5: Start Services

```bash
cd /opt/ai-search
sudo docker-compose up -d
```

---

## 5. Verification

### Step 5.1: Check Services Status

```bash
# Check running containers
sudo docker-compose ps

# Should show:
# ai-search-backend     running
# ai-search-qdrant      running
```

### Step 5.2: View Logs

```bash
# View all logs
sudo docker-compose logs

# View backend logs
sudo docker-compose logs backend

# Follow logs in real-time
sudo docker-compose logs -f
```

### Step 5.3: Test Application

**Get public IP:**
```bash
curl http://checkip.amazonaws.com
```

**Access application:**
- Web Interface: `http://<your-ec2-ip>:8000`
- API Docs: `http://<your-ec2-ip>:8000/docs`
- Qdrant Dashboard: `http://<your-ec2-ip>:6333/dashboard`

**Test file upload:**
1. Open the web interface
2. Upload a test PDF or document
3. Verify it appears in "Uploaded Documents"
4. Perform a search query
5. Check S3 bucket for uploaded file:
   ```bash
   aws s3 ls s3://plfs-han-ai-search/uploads/ --region us-west-2
   ```

### Step 5.4: Verify AWS Integrations

**Check Secrets Manager:**
```bash
# From EC2 instance
python tests/test_aws_secrets.py
```

**Check S3 Storage:**
```bash
# From EC2 instance
python tests/test_s3_storage.py
```

---

## 6. Troubleshooting

### Problem: Cannot Access Secrets Manager

**Symptoms:**
```
ERROR - Failed to load OpenAI API key from AWS Secrets Manager: Access Denied
```

**Solution:**
1. Verify IAM role is attached to EC2 instance
2. Check IAM policy includes `secretsmanager:GetSecretValue`
3. Verify secret name matches: `openai-api-key`
4. Check region is `us-west-2`

**Test:**
```bash
aws secretsmanager get-secret-value \
    --secret-id openai-api-key \
    --region us-west-2
```

### Problem: Cannot Access S3 Bucket

**Symptoms:**
```
WARNING - Failed to upload file to S3: Access Denied
```

**Solution:**
1. Verify IAM role includes S3 permissions
2. Check bucket name: `plfs-han-ai-search`
3. Verify bucket exists:
   ```bash
   aws s3 ls s3://plfs-han-ai-search --region us-west-2
   ```

### Problem: Services Won't Start

**Symptoms:**
```
ERROR: Cannot connect to Qdrant
```

**Solution:**
```bash
# Check Docker is running
sudo systemctl status docker

# Restart Docker
sudo systemctl restart docker

# Restart services
cd /opt/ai-search
sudo docker-compose down
sudo docker-compose up -d

# Check logs
sudo docker-compose logs
```

### Problem: Out of Memory

**Symptoms:**
```
Killed by signal 9
```

**Solution:**
1. Upgrade to larger instance (t3.large or t3.xlarge)
2. Or reduce memory usage:
   ```env
   # Use smaller embedding model
   EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
   ```

### Problem: Can't Connect to Web Interface

**Solution:**
1. Check security group allows port 8000
2. Verify services are running: `sudo docker-compose ps`
3. Check if application is listening:
   ```bash
   sudo netstat -tlnp | grep 8000
   ```

### Problem: Slow PDF Processing

**Solution:**
Already using o4-mini which is faster. If still slow:
1. Check OpenAI API rate limits
2. Verify network connectivity to OpenAI
3. Consider upgrading instance type for more CPU

---

## Configuration Summary

### Development Setup (Local)

```env
USE_AWS_SECRETS=false
OPENAI_API_KEY=sk-your-key-here
USE_S3_STORAGE=false
QDRANT_HOST=localhost
VISION_MODEL=o4-mini
```

### Production Setup (EC2)

```env
USE_AWS_SECRETS=true
AWS_SECRET_NAME_OPENAI=openai-api-key
AWS_REGION=us-west-2

USE_S3_STORAGE=true
AWS_S3_BUCKET=plfs-han-ai-search
S3_UPLOAD_PREFIX=uploads/

QDRANT_HOST=qdrant
VISION_MODEL=o4-mini
```

---

## Useful Commands

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

# Check AWS credentials
aws sts get-caller-identity

# Test Secrets Manager
python tests/test_aws_secrets.py

# Test S3
python tests/test_s3_storage.py

# Check disk space
df -h

# Check memory usage
free -m

# Check running containers
sudo docker ps
```

---

## Next Steps

1. ✅ Set up AWS Secrets Manager
2. ✅ Configure S3 storage
3. ✅ Test integrations locally
4. ✅ Deploy to EC2
5. ⏳ Set up Nginx reverse proxy (optional)
6. ⏳ Configure SSL/HTTPS (optional)
7. ⏳ Set up CloudWatch monitoring (optional)
8. ⏳ Configure automatic backups

---

**Need Help?** Check:
- Full deployment guide: [DEPLOYMENT_AWS.md](DEPLOYMENT_AWS.md)
- AWS Secrets setup: [AWS_SECRETS_SETUP.md](AWS_SECRETS_SETUP.md)
- Main documentation: [README.md](README.md)
