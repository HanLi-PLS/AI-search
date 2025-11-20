#!/bin/bash

# Setup script for security configuration
# Automatically configures .env file with required security settings

set -e  # Exit on error

echo "=========================================="
echo "AI Search - Security Configuration Setup"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if .env exists
if [ -f ".env" ]; then
    echo -e "${YELLOW}Warning: .env file already exists${NC}"
    read -p "Do you want to update it? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Setup cancelled."
        exit 0
    fi
    # Backup existing .env
    cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
    echo -e "${GREEN}✓ Backed up existing .env file${NC}"
fi

# Copy from example if .env doesn't exist
if [ ! -f ".env" ]; then
    if [ -f "backend/.env.example" ]; then
        cp backend/.env.example .env
        echo -e "${GREEN}✓ Created .env from backend/.env.example${NC}"
    elif [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${GREEN}✓ Created .env from .env.example${NC}"
    else
        echo -e "${RED}Error: No .env.example file found${NC}"
        exit 1
    fi
fi

echo ""
echo "Configuring security settings..."
echo ""

# Generate SECRET_KEY
echo "Generating SECRET_KEY..."
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
echo -e "${GREEN}✓ SECRET_KEY generated${NC}"

# Prompt for domain
echo ""
echo "Enter your domain(s) for CORS configuration"
echo "Example: https://pivotalbiovpai.com,https://www.pivotalbiovpai.com"
read -p "Domain(s) [press Enter for localhost default]: " DOMAIN_INPUT

if [ -z "$DOMAIN_INPUT" ]; then
    CORS_ORIGINS="http://localhost:5173,http://localhost:3000"
    echo -e "${YELLOW}Using default: $CORS_ORIGINS${NC}"
else
    CORS_ORIGINS="$DOMAIN_INPUT"
fi

# Prompt for environment
echo ""
read -p "Environment (production/development) [production]: " ENV_INPUT
ENVIRONMENT=${ENV_INPUT:-production}

# Update .env file
echo ""
echo "Updating .env file..."

# Function to update or add a key-value pair
update_env() {
    local key=$1
    local value=$2
    local file=".env"

    if grep -q "^${key}=" "$file"; then
        # Key exists, update it
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i '' "s|^${key}=.*|${key}=${value}|" "$file"
        else
            # Linux
            sed -i "s|^${key}=.*|${key}=${value}|" "$file"
        fi
    else
        # Key doesn't exist, add it
        echo "${key}=${value}" >> "$file"
    fi
}

# Update all security-related settings
update_env "SECRET_KEY" "$SECRET_KEY"
update_env "CORS_ORIGINS" "$CORS_ORIGINS"
update_env "CORS_ALLOW_CREDENTIALS" "true"
update_env "ENVIRONMENT" "$ENVIRONMENT"

# Add rate limiting settings if they don't exist
if ! grep -q "^RATE_LIMIT_DEFAULT=" .env; then
    echo "" >> .env
    echo "# Rate Limiting" >> .env
    echo "RATE_LIMIT_DEFAULT=60/minute" >> .env
    echo "RATE_LIMIT_SEARCH=20/minute" >> .env
    echo "RATE_LIMIT_UPLOAD=10/minute" >> .env
    echo "RATE_LIMIT_AUTH=5/minute" >> .env
fi

echo -e "${GREEN}✓ Configuration complete${NC}"
echo ""
echo "=========================================="
echo "Configuration Summary:"
echo "=========================================="
echo "SECRET_KEY: [Generated - ${#SECRET_KEY} characters]"
echo "CORS_ORIGINS: $CORS_ORIGINS"
echo "ENVIRONMENT: $ENVIRONMENT"
echo "RATE_LIMIT_DEFAULT: 60/minute"
echo "RATE_LIMIT_SEARCH: 20/minute"
echo "RATE_LIMIT_UPLOAD: 10/minute"
echo "RATE_LIMIT_AUTH: 5/minute"
echo ""
echo -e "${GREEN}✓ Setup complete!${NC}"
echo ""
echo "Your .env file has been configured with secure settings."
echo "You can now restart your services with: pm2 restart all"
echo ""
