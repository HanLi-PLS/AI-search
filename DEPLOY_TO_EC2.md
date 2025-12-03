# 🚀 Deploy to EC2 - Update Live Webpage

## Quick Deploy Commands

SSH into your EC2 instance and run these commands:

```bash
# 1. Navigate to project directory
cd /opt/ai-search  # or wherever your project is located

# 2. Pull latest changes from the branch
git fetch origin
git checkout claude/evaluate-html-to-react-016HeHCK7Xz9tY4UPcRqZWyn
git pull origin claude/evaluate-html-to-react-016HeHCK7Xz9tY4UPcRqZWyn

# 3. Install/update backend dependencies (if needed)
cd backend
source venv/bin/activate  # or: . venv/bin/activate
pip install -r requirements.txt

# 4. Rebuild frontend
cd ../frontend
npm install  # Install any new dependencies
npm run build  # Build production bundle

# 5. Restart services with PM2
cd ..
pm2 restart all

# Or restart specific services:
# pm2 restart ai-search-backend
# pm2 restart ai-search-frontend

# 6. Verify services are running
pm2 status
pm2 logs --lines 50  # Check for any errors
```

## Step-by-Step Explanation

### 1. Pull Latest Code
```bash
cd /opt/ai-search
git fetch origin
git checkout claude/evaluate-html-to-react-016HeHCK7Xz9tY4UPcRqZWyn
git pull origin claude/evaluate-html-to-react-016HeHCK7Xz9tY4UPcRqZWyn
```

### 2. Update Backend (if dependencies changed)
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
deactivate
```

**Note**: Only needed if `requirements.txt` was modified. For this update (documentation only), you can skip this.

### 3. Rebuild Frontend
```bash
cd frontend
npm install  # Install any new packages
npm run build  # Creates production build in dist/
```

This is crucial! The frontend must be rebuilt to include any new features or changes.

### 4. Restart PM2 Services
```bash
cd ..  # Back to project root
pm2 restart all
```

Or restart individual services:
```bash
pm2 restart ai-search-backend
pm2 restart ai-search-frontend
```

### 5. Verify Deployment
```bash
# Check service status
pm2 status

# View logs (last 50 lines)
pm2 logs --lines 50

# Follow logs in real-time
pm2 logs

# Check specific service
pm2 logs ai-search-backend
pm2 logs ai-search-frontend
```

## Troubleshooting

### If PM2 isn't running:
```bash
# Check if PM2 is installed
pm2 --version

# If not installed:
npm install -g pm2

# Start services
cd /opt/ai-search
pm2 start ecosystem.config.js
pm2 save
```

### If backend won't start:
```bash
# Check Python path
which python3

# Check if virtual environment is activated
source backend/venv/bin/activate
which python

# Test backend manually
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

### If frontend won't build:
```bash
# Clear cache and reinstall
cd frontend
rm -rf node_modules package-lock.json dist
npm install
npm run build

# Check build output
ls -la dist/
```

### Check if services are accessible:
```bash
# Backend health check
curl http://localhost:8000/api/health

# Frontend (if using nginx)
curl http://localhost:5173

# Or check actual frontend files
curl http://localhost:5173/index.html
```

## Quick One-Liner Deploy

For documentation-only updates (like this one), use this single command:

```bash
cd /opt/ai-search && git pull origin claude/evaluate-html-to-react-016HeHCK7Xz9tY4UPcRqZWyn && cd frontend && npm run build && cd .. && pm2 restart all && pm2 status
```

## Verify the Update

After deployment, check:

1. **Open browser**: Visit your EC2 public IP or domain
2. **Check Stock Tracker**: Navigate to stock tracker page
3. **Look for**:
   - The feature is already there! No UI changes in this update
   - New files are documentation only (not visible in UI)

## View Documentation Files

The new files are server-side only:
```bash
# View the documentation
cat /opt/ai-search/AI_NEWS_ANALYSIS_FEATURE.md

# Run test script
cd /opt/ai-search
python3 test_news_analysis.py

# Download demo HTML to view locally
# (From your local machine)
scp ec2-user@your-ec2-ip:/opt/ai-search/demo_news_analysis.html .
open demo_news_analysis.html
```

## PM2 Useful Commands

```bash
# View all processes
pm2 status

# View logs
pm2 logs

# Restart a specific service
pm2 restart ai-search-backend

# Stop a service
pm2 stop ai-search-backend

# Delete a service
pm2 delete ai-search-backend

# Save current PM2 configuration
pm2 save

# View detailed process info
pm2 show ai-search-backend
```

## Automated Deploy Script

Create this script for future deployments:

```bash
#!/bin/bash
# deploy.sh - Automated deployment script

set -e  # Exit on any error

echo "🚀 Starting deployment..."

# Navigate to project
cd /opt/ai-search

# Pull latest code
echo "📥 Pulling latest code..."
git fetch origin
git checkout claude/evaluate-html-to-react-016HeHCK7Xz9tY4UPcRqZWyn
git pull origin claude/evaluate-html-to-react-016HeHCK7Xz9tY4UPcRqZWyn

# Update backend (if needed)
echo "🐍 Updating backend..."
cd backend
source venv/bin/activate
pip install -r requirements.txt --quiet
deactivate

# Rebuild frontend
echo "⚛️  Building frontend..."
cd ../frontend
npm install --silent
npm run build

# Restart services
echo "♻️  Restarting services..."
cd ..
pm2 restart all

# Check status
echo "✅ Deployment complete!"
pm2 status

echo ""
echo "🌐 Your website is updated!"
echo "Visit: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)"
```

Make it executable:
```bash
chmod +x deploy.sh
./deploy.sh
```

## Important Notes

1. **This update is documentation only** - The AI news analysis feature was already implemented
2. **No database changes** - Safe to deploy without migrations
3. **No environment variable changes** - No `.env` updates needed
4. **Frontend rebuild required** - Even though no code changed, rebuilding ensures consistency

## What Changed in This Update

- ✅ Added `AI_NEWS_ANALYSIS_FEATURE.md` - Documentation
- ✅ Added `demo_news_analysis.html` - Visual demo
- ✅ Added `test_news_analysis.py` - Test script

The actual feature is already live and working!
