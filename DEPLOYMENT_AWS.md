# AWS Deployment Guide

This guide walks you through deploying the AI Document Search Tool on AWS EC2.

## Prerequisites

- AWS Account with EC2 access
- SSH key pair for EC2 access
- OpenAI API key
- (Optional) AWS S3 bucket for file storage

## Architecture Overview

```
Internet → AWS EC2 Instance
           ├── Docker: FastAPI Backend (Port 8000)
           ├── Docker: Qdrant Vector DB (Port 6333)
           └── (Optional) Nginx Reverse Proxy (Port 80/443)
```

## Step 1: Launch EC2 Instance

### Recommended Instance Type
- **Development**: t3.medium (2 vCPU, 4 GB RAM)
- **Production**: t3.large or c5.xlarge (for better embedding performance)

### Launch Instance

1. **Go to EC2 Console** → Launch Instance

2. **Choose AMI**:
   - Amazon Linux 2023 or Ubuntu 22.04 LTS

3. **Instance Type**:
   - Select t3.medium or larger

4. **Configure Instance**:
   - Enable Auto-assign Public IP

5. **Add Storage**:
   - Minimum: 30 GB gp3
   - Recommended: 50-100 GB for document storage

6. **Security Group**:
   ```
   Type            Protocol    Port    Source
   SSH             TCP         22      Your IP
   Custom TCP      TCP         8000    0.0.0.0/0
   HTTP            TCP         80      0.0.0.0/0 (if using Nginx)
   HTTPS           TCP         443     0.0.0.0/0 (if using SSL)
   ```

7. **Review and Launch**
   - Select or create a key pair
   - Download the .pem file

## Step 2: Connect to EC2 Instance

```bash
# Make key file secure
chmod 400 your-key.pem

# Connect to instance
ssh -i your-key.pem ec2-user@<your-instance-public-ip>
```

## Step 3: Install Docker

### For Amazon Linux 2023

```bash
# Update system
sudo yum update -y

# Install Docker
sudo yum install -y docker

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group
sudo usermod -a -G docker ec2-user

# Log out and log back in for group changes to take effect
exit
# Reconnect via SSH
```

### For Ubuntu

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker ubuntu

# Log out and log back in
exit
# Reconnect via SSH
```

## Step 4: Install Docker Compose

```bash
# Download Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# Make it executable
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker-compose --version
```

## Step 5: Deploy Application

### Clone Repository

```bash
# Install git if not already installed
sudo yum install -y git  # Amazon Linux
# OR
sudo apt-get install -y git  # Ubuntu

# Clone repository
git clone <your-repository-url>
cd AI-search
```

### Configure Environment

```bash
# Create .env file
cp .env.example .env

# Edit .env file
nano .env
```

**Required environment variables**:
```env
OPENAI_API_KEY=your-openai-api-key-here
QDRANT_HOST=qdrant
QDRANT_PORT=6333
API_HOST=0.0.0.0
API_PORT=8000
```

**Optional S3 integration**:
```env
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-west-2
AWS_S3_BUCKET=your-bucket-name
```

### Start Services

```bash
# Start the application
./start.sh

# Or manually with docker-compose
docker-compose up -d

# Check logs
docker-compose logs -f
```

## Step 6: Access Application

1. **Get your EC2 public IP**:
   ```bash
   curl http://checkip.amazonaws.com
   ```

2. **Access the web interface**:
   - URL: `http://<your-ec2-public-ip>:8000`

3. **Test the application**:
   - Upload a test document
   - Perform a search query

## Step 7: Set Up Nginx (Optional but Recommended)

### Install Nginx

```bash
# Amazon Linux
sudo yum install -y nginx

# Ubuntu
sudo apt-get install -y nginx
```

### Configure Nginx

```bash
sudo nano /etc/nginx/conf.d/ai-search.conf
```

Add the following configuration:

```nginx
server {
    listen 80;
    server_name your-domain.com;  # Or use your EC2 IP

    client_max_body_size 100M;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support (if needed in future)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Start Nginx

```bash
# Test configuration
sudo nginx -t

# Start Nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

Now access via: `http://<your-ec2-public-ip>` (port 80)

## Step 8: Set Up SSL/HTTPS (Optional)

### Using Let's Encrypt (Free SSL)

```bash
# Install Certbot
sudo yum install -y certbot python3-certbot-nginx  # Amazon Linux
# OR
sudo apt-get install -y certbot python3-certbot-nginx  # Ubuntu

# Get SSL certificate
sudo certbot --nginx -d your-domain.com

# Certbot will automatically configure Nginx for HTTPS
```

### Auto-renewal

```bash
# Test renewal
sudo certbot renew --dry-run

# Renewal is automatic via cron/systemd timer
```

## Step 9: Set Up Auto-Start on Reboot

```bash
# Create systemd service
sudo nano /etc/systemd/system/ai-search.service
```

Add:

```ini
[Unit]
Description=AI Document Search Tool
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/ec2-user/AI-search
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
User=ec2-user

[Install]
WantedBy=multi-user.target
```

Enable the service:

```bash
sudo systemctl enable ai-search.service
sudo systemctl start ai-search.service
```

## Step 10: Monitoring and Maintenance

### View Logs

```bash
# Application logs
docker-compose logs -f backend

# Qdrant logs
docker-compose logs -f qdrant

# All logs
docker-compose logs -f
```

### Check Resource Usage

```bash
# Container stats
docker stats

# Disk usage
df -h

# Memory usage
free -m
```

### Backup Qdrant Data

```bash
# Create backup
sudo tar -czf qdrant-backup-$(date +%Y%m%d).tar.gz qdrant_storage/

# Copy to S3 (if configured)
aws s3 cp qdrant-backup-*.tar.gz s3://your-backup-bucket/
```

### Update Application

```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose down
docker-compose up -d --build
```

## Troubleshooting

### Can't Access Application

1. Check security group allows port 8000
2. Verify services are running: `docker-compose ps`
3. Check logs: `docker-compose logs`

### Out of Memory

1. Check instance type (upgrade to larger instance)
2. Monitor memory: `free -m`
3. Consider using lighter embedding model

### Qdrant Connection Issues

```bash
# Restart Qdrant
docker-compose restart qdrant

# Check Qdrant logs
docker-compose logs qdrant
```

## Production Checklist

- [ ] Use strong security group rules
- [ ] Set up SSL/HTTPS
- [ ] Configure automatic backups
- [ ] Set up CloudWatch monitoring
- [ ] Use Elastic IP for static IP
- [ ] Set up auto-scaling (if needed)
- [ ] Configure log rotation
- [ ] Set up alerts for errors
- [ ] Use secrets manager for API keys
- [ ] Set up VPC for better security

## Cost Optimization

1. **Use Reserved Instances** for long-term deployments
2. **Stop during non-business hours** if not needed 24/7
3. **Use Spot Instances** for development
4. **Monitor data transfer costs**
5. **Use S3 Intelligent-Tiering** for stored documents

## Support

For deployment issues, check:
- Application logs: `docker-compose logs`
- System logs: `journalctl -u ai-search`
- EC2 instance health in AWS Console

---

**Estimated Monthly Cost** (us-east-1):
- t3.medium: ~$30/month
- 50 GB storage: ~$5/month
- Data transfer: ~$5-10/month
- **Total**: ~$40-45/month
