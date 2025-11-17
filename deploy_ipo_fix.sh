#!/bin/bash

echo "=========================================="
echo "IPO Tracker Fix Deployment"
echo "=========================================="

EC2_HOST="ec2-user@ec2-44-233-7-216.us-west-2.compute.amazonaws.com"
KEY_PATH="$HOME/.ssh/han-keypair-uswest2.pem"
BRANCH="claude/evaluate-html-to-react-016HeHCK7Xz9tY4UPcRqZWyn"

echo "Deploying IPO tracker fix to EC2..."
echo "Branch: $BRANCH"
echo ""

# Deploy backend only (no frontend changes)
ssh -i "$KEY_PATH" "$EC2_HOST" << 'ENDSSH'
    cd /opt/ai-search

    echo "Pulling latest code..."
    git fetch origin
    git checkout claude/evaluate-html-to-react-016HeHCK7Xz9tY4UPcRqZWyn
    git pull origin claude/evaluate-html-to-react-016HeHCK7Xz9tY4UPcRqZWyn

    echo "Restarting backend..."
    pm2 restart backend

    echo "Deployment complete!"
    pm2 status
ENDSSH

echo ""
echo "=========================================="
echo "Deployment Complete"
echo "=========================================="
echo "Test the IPO tracker at: http://44.233.7.216:3000"
