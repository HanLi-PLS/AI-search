#!/bin/bash

###############################################################################
# AI Document Search Tool - EC2 Setup Automation Script
#
# This script automates the setup of the AI Document Search Tool on EC2
#
# Prerequisites:
#   - Fresh EC2 instance (Amazon Linux 2023 or Ubuntu 22.04)
#   - SSH access to the instance
#   - IAM role attached with permissions for Secrets Manager and S3
#
# Usage:
#   1. SSH into your EC2 instance
#   2. wget https://raw.githubusercontent.com/your-repo/AI-search/main/scripts/setup_ec2.sh
#   3. chmod +x setup_ec2.sh
#   4. sudo ./setup_ec2.sh
#
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/HanLi-PLS/AI-search.git"
BRANCH="claude/ai-search-tool-011CUMmPzfCZLdSZBjHwvmT8"
INSTALL_DIR="/opt/ai-search"
SERVICE_USER="ai-search"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}AI Document Search - EC2 Setup${NC}"
echo -e "${BLUE}========================================${NC}"

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VERSION=$VERSION_ID
    echo -e "${GREEN}✓${NC} Detected OS: $OS $VERSION"
else
    echo -e "${RED}✗${NC} Cannot detect OS"
    exit 1
fi

# Update system
echo -e "\n${YELLOW}[1/10]${NC} Updating system packages..."
if [ "$OS" = "amzn" ] || [ "$OS" = "rhel" ] || [ "$OS" = "centos" ]; then
    sudo yum update -y
elif [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
    sudo apt-get update
    sudo apt-get upgrade -y
fi
echo -e "${GREEN}✓${NC} System updated"

# Install Docker
echo -e "\n${YELLOW}[2/10]${NC} Installing Docker..."
if ! command -v docker &> /dev/null; then
    if [ "$OS" = "amzn" ] || [ "$OS" = "rhel" ] || [ "$OS" = "centos" ]; then
        sudo yum install -y docker
        sudo systemctl start docker
        sudo systemctl enable docker
    elif [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        rm get-docker.sh
    fi
    echo -e "${GREEN}✓${NC} Docker installed"
else
    echo -e "${GREEN}✓${NC} Docker already installed"
fi

# Add current user to docker group
sudo usermod -aG docker ${USER}

# Install Docker Compose
echo -e "\n${YELLOW}[3/10]${NC} Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo -e "${GREEN}✓${NC} Docker Compose installed"
else
    echo -e "${GREEN}✓${NC} Docker Compose already installed"
fi

# Verify Docker installation
echo -e "\n${YELLOW}[4/10]${NC} Verifying Docker installation..."
docker --version
docker-compose --version
echo -e "${GREEN}✓${NC} Docker verification complete"

# Install Git
echo -e "\n${YELLOW}[5/10]${NC} Installing Git..."
if ! command -v git &> /dev/null; then
    if [ "$OS" = "amzn" ] || [ "$OS" = "rhel" ] || [ "$OS" = "centos" ]; then
        sudo yum install -y git
    elif [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
        sudo apt-get install -y git
    fi
    echo -e "${GREEN}✓${NC} Git installed"
else
    echo -e "${GREEN}✓${NC} Git already installed"
fi

# Clone repository
echo -e "\n${YELLOW}[6/10]${NC} Cloning repository..."
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}⚠${NC}  Directory $INSTALL_DIR already exists"
    read -p "Remove and re-clone? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo rm -rf $INSTALL_DIR
        sudo git clone -b $BRANCH $REPO_URL $INSTALL_DIR
        echo -e "${GREEN}✓${NC} Repository cloned"
    else
        echo -e "${YELLOW}⚠${NC}  Using existing directory"
    fi
else
    sudo git clone -b $BRANCH $REPO_URL $INSTALL_DIR
    echo -e "${GREEN}✓${NC} Repository cloned"
fi

cd $INSTALL_DIR

# Create service user
echo -e "\n${YELLOW}[7/10]${NC} Setting up service user..."
if ! id "$SERVICE_USER" &>/dev/null; then
    sudo useradd -r -s /bin/false $SERVICE_USER
    echo -e "${GREEN}✓${NC} Service user created"
else
    echo -e "${GREEN}✓${NC} Service user already exists"
fi

# Set permissions
sudo chown -R $SERVICE_USER:$SERVICE_USER $INSTALL_DIR

# Configure environment
echo -e "\n${YELLOW}[8/10]${NC} Configuring environment..."
if [ ! -f "$INSTALL_DIR/.env" ]; then
    echo -e "${BLUE}Creating .env file...${NC}"
    sudo cp $INSTALL_DIR/.env.example $INSTALL_DIR/.env

    echo -e "${YELLOW}Please provide configuration:${NC}"

    # Ask for AWS Secrets Manager
    read -p "Use AWS Secrets Manager for OpenAI API key? (y/n): " use_secrets
    if [[ $use_secrets =~ ^[Yy]$ ]]; then
        sudo sed -i 's/USE_AWS_SECRETS=false/USE_AWS_SECRETS=true/' $INSTALL_DIR/.env
        echo -e "${GREEN}✓${NC} Configured to use AWS Secrets Manager"
    else
        read -p "Enter OpenAI API key: " openai_key
        sudo sed -i "s/OPENAI_API_KEY=.*/OPENAI_API_KEY=$openai_key/" $INSTALL_DIR/.env
        echo -e "${GREEN}✓${NC} OpenAI API key configured"
    fi

    # Ask for S3 storage
    read -p "Use S3 for file storage? (y/n): " use_s3
    if [[ $use_s3 =~ ^[Yy]$ ]]; then
        sudo sed -i 's/USE_S3_STORAGE=false/USE_S3_STORAGE=true/' $INSTALL_DIR/.env
        echo -e "${GREEN}✓${NC} Configured to use S3 storage"
    fi

    # Set Qdrant host for Docker
    sudo sed -i 's/QDRANT_HOST=localhost/QDRANT_HOST=qdrant/' $INSTALL_DIR/.env

    echo -e "${GREEN}✓${NC} Environment configured"
else
    echo -e "${GREEN}✓${NC} .env file already exists"
fi

# Test AWS connectivity
echo -e "\n${YELLOW}[9/10]${NC} Testing AWS connectivity..."
if command -v aws &> /dev/null; then
    if aws sts get-caller-identity &> /dev/null; then
        echo -e "${GREEN}✓${NC} AWS credentials configured"
        aws sts get-caller-identity
    else
        echo -e "${YELLOW}⚠${NC}  AWS credentials not configured"
        echo "  Make sure IAM role is attached to EC2 instance"
    fi
else
    echo -e "${YELLOW}⚠${NC}  AWS CLI not installed"
fi

# Start services
echo -e "\n${YELLOW}[10/10]${NC} Starting services..."
cd $INSTALL_DIR
sudo docker-compose up -d

echo -e "\n${YELLOW}Waiting for services to start...${NC}"
sleep 10

# Check if services are running
if sudo docker-compose ps | grep -q "Up"; then
    echo -e "${GREEN}✓${NC} Services started successfully"

    # Get public IP
    PUBLIC_IP=$(curl -s http://checkip.amazonaws.com || echo "localhost")

    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}✓ Setup Complete!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo -e "\n${BLUE}Access your application:${NC}"
    echo -e "  Web Interface: http://$PUBLIC_IP:8000"
    echo -e "  API Docs:      http://$PUBLIC_IP:8000/docs"
    echo -e "  Qdrant:        http://$PUBLIC_IP:6333/dashboard"
    echo -e "\n${BLUE}Useful commands:${NC}"
    echo -e "  View logs:   cd $INSTALL_DIR && sudo docker-compose logs -f"
    echo -e "  Restart:     cd $INSTALL_DIR && sudo docker-compose restart"
    echo -e "  Stop:        cd $INSTALL_DIR && sudo docker-compose down"
    echo -e "  Update:      cd $INSTALL_DIR && git pull && sudo docker-compose up -d --build"
    echo -e "\n${BLUE}Next steps:${NC}"
    echo -e "  1. Configure security group to allow port 8000"
    echo -e "  2. (Optional) Set up Nginx reverse proxy for HTTPS"
    echo -e "  3. (Optional) Set up CloudWatch for monitoring"
    echo -e "${GREEN}========================================${NC}\n"
else
    echo -e "${RED}✗${NC} Failed to start services"
    echo -e "\n${YELLOW}Check logs:${NC} sudo docker-compose logs"
    exit 1
fi
