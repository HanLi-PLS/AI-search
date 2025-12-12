# Migration Guide: t3.xlarge → g4dn.xlarge Spot

## Step 1: Gather Current Instance Information

Run these commands on your LOCAL machine (not EC2):

```bash
# Set your instance ID (replace with your actual instance ID)
INSTANCE_ID="i-xxxxxxxxx"

# Get instance details
aws ec2 describe-instances \
  --instance-ids $INSTANCE_ID \
  --query 'Reservations[0].Instances[0].[InstanceId,SubnetId,SecurityGroups[*].GroupId,KeyName,IamInstanceProfile.Arn,BlockDeviceMappings[0].Ebs.VolumeId]' \
  --output table

# Save these values:
# - Instance ID: i-xxxxxxxxx
# - Subnet ID: subnet-xxxxxxxxx
# - Security Group ID: sg-xxxxxxxxx
# - Key Name: your-key-name
# - IAM Role: your-iam-role
# - Volume ID: vol-xxxxxxxxx
```

## Step 2: Create AMI Backup (Safety Net)

```bash
# Create AMI from current instance
AMI_ID=$(aws ec2 create-image \
  --instance-id $INSTANCE_ID \
  --name "ai-search-backup-$(date +%Y%m%d-%H%M%S)" \
  --description "Backup before switching to g4dn.xlarge Spot" \
  --no-reboot \
  --query 'ImageId' \
  --output text)

echo "AMI created: $AMI_ID"

# Wait for AMI to be ready
aws ec2 wait image-available --image-ids $AMI_ID
echo "AMI is ready!"
```

## Step 3: Configure EBS for Persistence

```bash
# Get the root volume ID
VOLUME_ID=$(aws ec2 describe-instances \
  --instance-ids $INSTANCE_ID \
  --query 'Reservations[0].Instances[0].BlockDeviceMappings[0].Ebs.VolumeId' \
  --output text)

echo "Volume ID: $VOLUME_ID"

# Set Delete on Termination = false (prevents data loss)
aws ec2 modify-instance-attribute \
  --instance-id $INSTANCE_ID \
  --block-device-mappings "[{\"DeviceName\":\"/dev/xvda\",\"Ebs\":{\"DeleteOnTermination\":false}}]"

echo "✅ EBS volume will persist on termination"
```

## Step 4: Stop Current Instance

```bash
# Notify users about maintenance
echo "⚠️ NOTIFY USERS: 5-minute maintenance window starting now"

# Stop the instance (preserves EBS volume)
aws ec2 stop-instances --instance-ids $INSTANCE_ID

# Wait for it to stop
aws ec2 wait instance-stopped --instance-ids $INSTANCE_ID
echo "✅ Instance stopped"
```

## Step 5: Launch g4dn.xlarge Spot Instance

```bash
# Get values from Step 1
SUBNET_ID="subnet-xxxxxxxxx"  # Replace with your value
SECURITY_GROUP="sg-xxxxxxxxx"  # Replace with your value
KEY_NAME="your-key-name"        # Replace with your value
IAM_ROLE="your-iam-role-name"   # Replace with your value (just the name, not full ARN)

# Launch g4dn.xlarge Spot with same configuration
SPOT_REQUEST=$(aws ec2 run-instances \
  --image-id $AMI_ID \
  --instance-type g4dn.xlarge \
  --subnet-id $SUBNET_ID \
  --security-group-ids $SECURITY_GROUP \
  --key-name $KEY_NAME \
  --iam-instance-profile Name=$IAM_ROLE \
  --instance-market-options '{
    "MarketType": "spot",
    "SpotOptions": {
      "SpotInstanceType": "persistent",
      "InstanceInterruptionBehavior": "stop"
    }
  }' \
  --block-device-mappings '[
    {
      "DeviceName": "/dev/xvda",
      "Ebs": {
        "VolumeSize": 30,
        "VolumeType": "gp3",
        "DeleteOnTermination": false
      }
    }
  ]' \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=ai-search-gpu}]' \
  --query 'Instances[0].InstanceId' \
  --output text)

echo "New Spot Instance ID: $SPOT_REQUEST"

# Wait for instance to be running
aws ec2 wait instance-running --instance-ids $SPOT_REQUEST
echo "✅ Spot instance is running!"

# Get public IP
NEW_IP=$(aws ec2 describe-instances \
  --instance-ids $SPOT_REQUEST \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text)

echo "New Public IP: $NEW_IP"
```

## Step 6: Copy Data from Old Volume to New Instance

```bash
# SSH to new instance
ssh -i your-key.pem ec2-user@$NEW_IP

# On the new instance, the AMI already has your code
# Just need to pull latest changes
cd /opt/ai-search
git pull origin claude/upgrade-document-search-0146g7aVkVoKHACRKoW3X4y4

# Restart backend
pm2 restart ai-search-backend

# Check if GPU is available
python3 -c "import torch; print(f'GPU available: {torch.cuda.is_available()}')"
# Should print: GPU available: True
```

## Step 7: Update DNS/IP (if using domain)

```bash
# If you're using a domain with Route53, update the A record
# Replace with your hosted zone ID and domain
HOSTED_ZONE_ID="Z123456789ABC"
DOMAIN="pivotalbiovpai.com"

# Create change batch
cat > /tmp/change-batch.json <<EOF
{
  "Changes": [{
    "Action": "UPSERT",
    "ResourceRecordSet": {
      "Name": "$DOMAIN",
      "Type": "A",
      "TTL": 300,
      "ResourceRecords": [{"Value": "$NEW_IP"}]
    }
  }]
}
EOF

# Update DNS
aws route53 change-resource-record-sets \
  --hosted-zone-id $HOSTED_ZONE_ID \
  --change-batch file:///tmp/change-batch.json

echo "✅ DNS updated"
```

## Step 8: Set Up Log Rotation (Prevent Disk Fill)

SSH to new instance and run:

```bash
# Install PM2 log rotation
pm2 install pm2-logrotate

# Configure log rotation
pm2 set pm2-logrotate:max_size 100M
pm2 set pm2-logrotate:retain 5
pm2 set pm2-logrotate:compress true

# Save PM2 config
pm2 save

echo "✅ Log rotation configured"
```

## Step 9: Set Up Spot Interruption Monitoring (Optional)

Create a script to monitor Spot interruption warnings:

```bash
# Create monitoring script
sudo tee /usr/local/bin/spot-monitor.sh > /dev/null <<'EOF'
#!/bin/bash
# Check for Spot interruption notice
if curl -s http://169.254.169.254/latest/meta-data/spot/instance-action | grep -q action; then
  echo "⚠️ Spot interruption detected! Instance will terminate in 2 minutes"
  # Optional: Send notification (email, Slack, etc.)
  # For now, just log it
  logger "SPOT INTERRUPTION DETECTED"
fi
EOF

sudo chmod +x /usr/local/bin/spot-monitor.sh

# Add to crontab (check every minute)
(crontab -l 2>/dev/null; echo "* * * * * /usr/local/bin/spot-monitor.sh") | crontab -

echo "✅ Spot interruption monitoring enabled"
```

## Step 10: Test Everything

```bash
# 1. Check backend is running
curl http://localhost:8000/api/health

# 2. Check GPU is recognized
python3 -c "import torch; print(torch.cuda.get_device_name(0))"
# Should show: Tesla T4

# 3. Upload a test PDF and verify speed improvement

# 4. Check memory usage
free -h

# 5. Check disk usage
df -h /
```

## Step 11: Cleanup Old Instance (After Confirming Everything Works)

```bash
# Keep old instance stopped for a few days as backup
# After you're confident everything works:

# Terminate old t3.xlarge instance
aws ec2 terminate-instances --instance-ids $INSTANCE_ID

# Note: The old EBS volume will persist (we set DeleteOnTermination=false)
# You can delete it manually after a week if everything is working fine:
# aws ec2 delete-volume --volume-id $VOLUME_ID
```

## Handling Spot Interruptions

**If your Spot instance gets interrupted:**

The instance will **stop** (not terminate) because we set `InstanceInterruptionBehavior: stop`

**To recover:**
1. Instance automatically stops (data persists on EBS)
2. Launch new g4dn.xlarge Spot instance from same AMI
3. Downtime: ~2-3 minutes

**Or manually restart the stopped Spot instance:**
```bash
aws ec2 start-instances --instance-ids $SPOT_REQUEST
```

## Cost Summary

**Before (t3.xlarge):**
- Instance: $0.166/hour = $120/month
- EBS (30GB): $2.40/month
- **Total: ~$122/month**

**After (g4dn.xlarge Spot):**
- Instance: $0.158/hour = $114/month
- EBS (30GB): $2.40/month
- **Total: ~$116/month**

**Savings: $6/month** + 7-12x faster PDF processing!

## Rollback Plan

**If anything goes wrong:**

```bash
# Start your old t3.xlarge instance
aws ec2 start-instances --instance-ids $INSTANCE_ID

# Terminate the Spot instance
aws ec2 terminate-instances --instance-ids $SPOT_REQUEST

# Update DNS back to old IP (if needed)
```

All your data is safe on the old EBS volume.
