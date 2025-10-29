# Create EC2 Instance - Step-by-Step Guide

This guide will walk you through creating an EC2 instance for the AI Document Search Tool with detailed pricing information.

## 💰 Cost Breakdown (Monthly Estimates)

### Option 1: Recommended Setup (t3.medium)
```
Component                   Cost/Month (US East/West)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EC2 t3.medium (24/7)        ~$30.00
50 GB gp3 Storage           ~$4.00
Data Transfer (5-10 GB)     ~$0.45-$0.90
S3 Storage (50 GB)          ~$1.15
S3 Requests (10K)           ~$0.04
Secrets Manager (1 secret)  ~$0.40
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOTAL                       ~$36-$37/month
```

### Option 2: Budget Setup (t3.small)
```
Component                   Cost/Month
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EC2 t3.small (24/7)         ~$15.00
30 GB gp3 Storage           ~$2.40
Data Transfer               ~$0.45
S3 Storage (20 GB)          ~$0.46
S3 Requests                 ~$0.04
Secrets Manager             ~$0.40
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOTAL                       ~$19/month
```

**⚠️ Note**: t3.small may be slower for large PDFs with images.

### Option 3: Development/Testing (part-time)
```
If you run the instance only 8 hours/day, 5 days/week:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EC2 t3.medium (40 hrs/week) ~$5.00
Storage (50 GB)             ~$4.00
Other services              ~$2.00
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOTAL                       ~$11/month
```

### 💡 Cost Optimization Tips

1. **Stop when not in use**: Stop (don't terminate) instance when not needed
2. **Reserved Instances**: Save 30-40% if committing to 1 year
3. **Spot Instances**: Save up to 90% (but can be interrupted)
4. **Right-size**: Monitor usage and downsize if underutilized

---

## 📋 Prerequisites

Before starting, you'll need:
- [ ] AWS Account (create at https://aws.amazon.com if needed)
- [ ] Credit card for billing
- [ ] OpenAI API key
- [ ] 15-20 minutes of your time

**Cost during setup**: ~$0.10 (for testing)

---

## 🚀 Step-by-Step Instance Creation

### Step 1: Log into AWS Console

1. Go to https://console.aws.amazon.com/
2. Sign in with your AWS account
3. **Select Region**: Choose **us-west-2** (Oregon) in top-right corner
   - This matches your S3 bucket and Secrets Manager configuration

### Step 2: Navigate to EC2

1. In the AWS Console, search for "EC2" in the top search bar
2. Click **EC2** (Virtual Servers in the Cloud)
3. Click **Launch instance** (orange button)

### Step 3: Configure Instance Basics

**Name and tags:**
```
Name: ai-search-production
```

**Application and OS Images (Amazon Machine Image):**
```
Quick Start: Amazon Linux
AMI: Amazon Linux 2023 AMI (default, free tier eligible)
Architecture: 64-bit (x86)
```

**Instance type:**

For production (recommended):
```
Instance type: t3.medium
- 2 vCPU
- 4 GB RAM
- ~$0.0416/hour = ~$30/month
```

For budget:
```
Instance type: t3.small
- 2 vCPU
- 2 GB RAM
- ~$0.0208/hour = ~$15/month
```

**💡 My Recommendation**: Start with **t3.medium**. You can always resize later.

### Step 4: Key Pair (SSH Access)

**Create new key pair:**
```
1. Click "Create new key pair"
2. Key pair name: ai-search-key
3. Key pair type: RSA
4. Private key format: .pem (for Mac/Linux) or .ppk (for Windows PuTTY)
5. Click "Create key pair"
```

**⚠️ IMPORTANT**: Save the downloaded `.pem` file safely! You'll need it to connect.

### Step 5: Network Settings

**Firewall (security groups):**

Click **"Edit"** next to Network settings, then configure:

```
Security group name: ai-search-sg
Description: Security group for AI Document Search

Add these rules:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Type            Port    Source      Description
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SSH             22      My IP       SSH access (auto-detects your IP)
Custom TCP      8000    Anywhere    AI Search application
HTTP            80      Anywhere    Nginx (optional, for future)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**To add rules:**
1. Click "Add security group rule"
2. Set Type, Port range, and Source as above
3. Repeat for each rule

**⚠️ Security Note**:
- Port 22 (SSH): Set to "My IP" for security
- Port 8000: Set to "Anywhere" (0.0.0.0/0) so you can access from any location

### Step 6: Configure Storage

```
Storage: 1 volume(s)

Volume 1 (Root):
- Size: 50 GiB (recommended) or 30 GiB (minimum)
- Volume type: gp3
- IOPS: 3000 (default)
- Throughput: 125 MB/s (default)
- Delete on termination: Yes (checked)
- Encrypted: No (optional, enable for extra security)
```

**Cost**: ~$4.00/month for 50 GB or ~$2.40/month for 30 GB

### Step 7: Advanced Details

**Scroll down to "Advanced details"** and configure:

**IAM instance profile:**
```
We'll create this in Step 8 - leave as "None" for now
```

Leave all other settings as default.

### Step 8: Review and Launch

**Summary (for t3.medium):**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AMI:               Amazon Linux 2023
Instance type:     t3.medium
Storage:           50 GB gp3
Security groups:   ai-search-sg (SSH, 8000, 80)
Key pair:          ai-search-key
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Estimated cost:    ~$0.0416/hour (~$30/month)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Click "Launch instance"**

🎉 **Your instance is being created!**

**Wait 2-3 minutes** for the instance to start.

---

## 🔐 Step 9: Create IAM Role (Critical!)

Your application needs permissions to access AWS Secrets Manager and S3.

### 9.1: Create IAM Policy

1. Go to **IAM** in AWS Console
2. Click **Policies** → **Create policy**
3. Click **JSON** tab
4. Paste this policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "SecretsManagerAccess",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "arn:aws:secretsmanager:us-west-2:*:secret:openai-api-key-*"
    },
    {
      "Sid": "S3BucketAccess",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::plfs-han-ai-search/*"
    },
    {
      "Sid": "S3ListBucket",
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::plfs-han-ai-search"
    }
  ]
}
```

5. Click **Next**
6. **Policy name**: `AISearchAppPolicy`
7. **Description**: `Permissions for AI Document Search application`
8. Click **Create policy**

### 9.2: Create IAM Role

1. Still in **IAM**, click **Roles** → **Create role**
2. **Trusted entity type**: AWS service
3. **Use case**: EC2
4. Click **Next**
5. **Search for**: `AISearchAppPolicy` (the policy you just created)
6. **Check the box** next to it
7. Click **Next**
8. **Role name**: `AISearchAppRole`
9. **Description**: `Role for AI Document Search EC2 instance`
10. Click **Create role**

### 9.3: Attach Role to EC2 Instance

1. Go back to **EC2** console
2. Find your instance (`ai-search-production`)
3. **Select** the instance (checkbox)
4. Click **Actions** → **Security** → **Modify IAM role**
5. **IAM role**: Select `AISearchAppRole`
6. Click **Update IAM role**

✅ **IAM role attached!** Your app can now access Secrets Manager and S3.

---

## 🔑 Step 10: Get Your Instance Connection Info

1. In EC2 console, select your instance
2. **Note these details:**

```
Instance ID:        i-0abc123def456789a (example)
Instance state:     Running ✅
Public IPv4 DNS:    ec2-XX-XXX-XXX-XX.us-west-2.compute.amazonaws.com
Public IPv4:        XX.XXX.XXX.XX ← THIS IS YOUR IP!
```

**Your website will be at**: `http://XX.XXX.XXX.XX:8000`

---

## 📊 What You've Created

```
┌────────────────────────────────────────────┐
│  EC2 Instance: ai-search-production        │
│  ├─ Type: t3.medium (2 vCPU, 4GB RAM)     │
│  ├─ OS: Amazon Linux 2023                  │
│  ├─ Storage: 50 GB gp3                     │
│  ├─ Security: SSH (22), HTTP (8000, 80)   │
│  └─ IAM Role: AISearchAppRole              │
│                                             │
│  Permissions:                               │
│  ✅ Secrets Manager (OpenAI key)           │
│  ✅ S3 (plfs-han-ai-search)                │
│                                             │
│  Cost: ~$30-36/month (if running 24/7)     │
└────────────────────────────────────────────┘
```

---

## 💳 Billing & Cost Monitoring

### View Current Costs

1. Go to **AWS Billing Dashboard**
2. Click **Bills** to see current month charges
3. Set up **Billing Alerts**:
   - Click **Budgets** → **Create budget**
   - Set alert at $50/month to get notified

### Stop Instance When Not in Use

To save costs:

```bash
# Stop instance (saves ~$30/month but keeps storage ~$4)
AWS Console → EC2 → Select instance → Instance state → Stop

# Start again when needed
AWS Console → EC2 → Select instance → Instance state → Start
```

**⚠️ Don't "Terminate"** - that deletes everything!

---

## 🎯 Cost Comparison Table

| Usage Pattern | Instance | Storage | Cost/Month |
|---------------|----------|---------|------------|
| 24/7 Production | t3.medium | 50 GB | ~$36 |
| 24/7 Budget | t3.small | 30 GB | ~$19 |
| 8hrs/day, 5days/week | t3.medium | 50 GB | ~$11 |
| Testing (10hrs total) | t3.medium | 50 GB | ~$4.40 |

---

## ✅ Checklist - Before Deployment

Make sure you have:

- [x] EC2 instance running (t3.medium or t3.small)
- [x] Security group configured (ports 22, 8000)
- [x] IAM role created and attached
- [x] SSH key downloaded (.pem file)
- [x] Public IP address noted

**Missing items? Create them now:**

### Need to Create S3 Bucket?

```bash
aws s3 mb s3://plfs-han-ai-search --region us-west-2
```

### Need to Create Secrets Manager Secret?

```bash
aws secretsmanager create-secret \
    --name openai-api-key \
    --description "OpenAI API key for AI Document Search" \
    --secret-string '{"key":"YOUR-OPENAI-API-KEY-HERE"}' \
    --region us-west-2
```

---

## 🚀 Next Steps

Now that your EC2 instance is created:

**1. Connect to your instance**

```bash
# Make key secure
chmod 400 ai-search-key.pem

# Connect (replace XX.XXX.XXX.XX with your IP)
ssh -i ai-search-key.pem ec2-user@XX.XXX.XXX.XX
```

**2. Deploy the application**

See [DEPLOY_NOW.md](DEPLOY_NOW.md) for deployment instructions.

Quick deploy command:
```bash
wget https://raw.githubusercontent.com/HanLi-PLS/AI-search/claude/ai-search-tool-011CUMmPzfCZLdSZBjHwvmT8/scripts/setup_ec2.sh
chmod +x setup_ec2.sh
sudo ./setup_ec2.sh
```

**3. Access your application**

```
http://YOUR-EC2-PUBLIC-IP:8000
```

---

## 💡 Pro Tips

1. **Elastic IP**: Free when attached to running instance, prevents IP changes
2. **CloudWatch**: Free basic monitoring included
3. **Auto-start on reboot**: Configured automatically by our setup script
4. **Backups**: Take snapshots of your volume periodically
5. **Free Tier**: First 750 hours/month of t3.micro is free for 12 months (new accounts)

---

## 🆘 Need Help?

Common issues:
- **Can't connect via SSH**: Check security group allows your IP on port 22
- **Website not loading**: Check security group allows 0.0.0.0/0 on port 8000
- **Access Denied errors**: Verify IAM role is attached to instance

Full troubleshooting: See [SETUP_TESTING_GUIDE.md](SETUP_TESTING_GUIDE.md)

---

## 📞 AWS Free Tier Reminder

**New AWS accounts get:**
- ✅ 750 hours/month of t3.micro for 12 months (FREE)
- ✅ 30 GB of EBS storage
- ✅ 5 GB S3 storage

**For this project:**
- t3.medium is NOT free tier (costs ~$30/month)
- But you can start with t3.micro for testing (FREE)
- Then upgrade to t3.medium for production

---

**Ready to create your instance? Follow the steps above!**

Once created, tell me your **public IP address** and I'll give you the exact website link! 🚀
