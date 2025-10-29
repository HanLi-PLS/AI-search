# AWS Secrets Manager Setup Guide

This guide explains how to configure the AI Document Search Tool to use AWS Secrets Manager for storing your OpenAI API key instead of storing it directly in the `.env` file.

## Why Use AWS Secrets Manager?

- **Security**: API keys are not stored in plain text files
- **Rotation**: Easy to rotate keys without changing code
- **Audit**: AWS CloudTrail tracks all access to secrets
- **Compliance**: Meets security compliance requirements
- **Team Access**: Centralized secret management for teams

## Prerequisites

- AWS Account with access to Secrets Manager
- AWS CLI configured or IAM credentials
- OpenAI API key

## Step 1: Store OpenAI API Key in AWS Secrets Manager

### Option A: Using AWS Console

1. **Go to AWS Secrets Manager Console**
   - Navigate to: https://console.aws.amazon.com/secretsmanager/

2. **Create New Secret**
   - Click "Store a new secret"
   - Select "Other type of secret"

3. **Configure Secret**
   - Key/value pairs:
     ```
     key: your-openai-api-key-here
     ```
   - Click "Next"

4. **Name Your Secret**
   - Secret name: `openai-api-key`
   - Description: "OpenAI API key for AI Document Search"
   - Click "Next"

5. **Configure Rotation** (Optional)
   - Skip for now unless you want automatic rotation
   - Click "Next"

6. **Review and Store**
   - Review settings and click "Store"

### Option B: Using AWS CLI

```bash
# Create the secret
aws secretsmanager create-secret \
    --name openai-api-key \
    --description "OpenAI API key for AI Document Search" \
    --secret-string '{"key":"your-openai-api-key-here"}' \
    --region us-west-2
```

### Verify Secret Creation

```bash
# Test retrieving the secret
aws secretsmanager get-secret-value \
    --secret-id openai-api-key \
    --region us-west-2
```

## Step 2: Configure IAM Permissions

Your EC2 instance or local development environment needs permission to access the secret.

### For EC2 Instance (Recommended)

1. **Create IAM Role** with this policy:

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
      "Resource": "arn:aws:secretsmanager:us-west-2:YOUR-ACCOUNT-ID:secret:openai-api-key-*"
    }
  ]
}
```

2. **Attach Role to EC2 Instance**
   - EC2 Console → Select instance → Actions → Security → Modify IAM role
   - Select the role you created

### For Local Development

Use AWS credentials with appropriate permissions:

```bash
# Configure AWS CLI
aws configure

# Or use environment variables
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_REGION=us-west-2
```

## Step 3: Configure Application

### Edit .env File

```bash
# Copy example file
cp .env.example .env

# Edit .env
nano .env
```

### Configuration Options

**Option 1: AWS Secrets Manager (Production)**

```env
# Enable AWS Secrets Manager
USE_AWS_SECRETS=true
AWS_SECRET_NAME_OPENAI=openai-api-key
AWS_REGION=us-west-2

# Leave OPENAI_API_KEY empty (it will be loaded from AWS)
OPENAI_API_KEY=

# Vision Model
VISION_MODEL=o4-mini
```

**Option 2: Direct API Key (Local Development)**

```env
# Use direct API key
USE_AWS_SECRETS=false

# Set API key directly
OPENAI_API_KEY=your-openai-api-key-here

# Vision Model
VISION_MODEL=o4-mini
```

## Step 4: Test Configuration

### Start the Application

```bash
./start.sh
```

### Verify in Logs

The application should start successfully and show:

```
INFO - Starting AI Search Tool...
INFO - Loading embedding model: sentence-transformers/all-MiniLM-L6-v2
```

If there's an error accessing the secret:

```
ERROR - Failed to load OpenAI API key from AWS Secrets Manager: ...
```

Check:
1. IAM permissions are correct
2. Secret name matches configuration
3. AWS region is correct
4. AWS credentials are available

## How It Works

The application uses this logic to load the OpenAI API key:

```python
# From backend/app/config.py

if USE_AWS_SECRETS and not OPENAI_API_KEY:
    # Load from AWS Secrets Manager
    from backend.app.utils.aws_secrets import get_key
    OPENAI_API_KEY = get_key(
        secret_name=AWS_SECRET_NAME_OPENAI,
        region_name=AWS_REGION
    )
else:
    # Use direct API key from .env
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
```

## Vision Model Configuration

The application now supports configurable vision models for PDF image processing:

### Available Models

- **o4-mini** (default)
  - Faster processing
  - Lower cost
  - Good for most use cases

- **gpt-4o**
  - Higher quality image understanding
  - Better for complex diagrams
  - Higher cost

### Configure Vision Model

In `.env`:

```env
# For o4-mini (default)
VISION_MODEL=o4-mini

# For gpt-4o
VISION_MODEL=gpt-4o
```

## Troubleshooting

### Error: "Unable to locate credentials"

**Solution**: Configure AWS credentials

```bash
# Option 1: AWS CLI
aws configure

# Option 2: Environment variables
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
export AWS_REGION=us-west-2

# Option 3: For EC2, attach IAM role
```

### Error: "Access Denied"

**Solution**: Check IAM permissions

```bash
# Test access
aws secretsmanager get-secret-value \
    --secret-id openai-api-key \
    --region us-west-2
```

### Error: "Secret not found"

**Solution**: Check secret name and region

```bash
# List all secrets
aws secretsmanager list-secrets --region us-west-2

# Verify secret exists
aws secretsmanager describe-secret \
    --secret-id openai-api-key \
    --region us-west-2
```

### Secret Not Loading on Startup

1. Check logs: `docker-compose logs backend`
2. Verify `.env` has `USE_AWS_SECRETS=true`
3. Ensure AWS credentials are available in container
4. Test AWS connection from container:

```bash
docker exec -it ai-search-backend bash
python -c "import boto3; print(boto3.client('secretsmanager', region_name='us-west-2').list_secrets())"
```

## Cost Considerations

AWS Secrets Manager pricing (as of 2025):
- **$0.40 per secret per month**
- **$0.05 per 10,000 API calls**

For this application:
- 1 secret (OpenAI API key): ~$0.40/month
- API calls: Minimal (only on startup)
- **Total**: < $1/month

## Security Best Practices

1. **Never commit API keys to git**
   - `.env` is in `.gitignore`
   - Use AWS Secrets Manager for production

2. **Use IAM roles for EC2**
   - Avoid storing AWS credentials on instance
   - Roles provide automatic credential rotation

3. **Restrict IAM permissions**
   - Only grant access to specific secrets
   - Use least privilege principle

4. **Enable CloudTrail**
   - Monitor secret access
   - Set up alerts for unusual activity

5. **Regular rotation**
   - Rotate OpenAI API key periodically
   - Update in Secrets Manager only (no code changes)

## Additional Secrets

You can store other secrets similarly:

```python
# Example: Add Azure key
azure_key = get_key("azure-doc-extraction-test-key", "us-west-2")
```

Create in AWS Secrets Manager:

```bash
aws secretsmanager create-secret \
    --name azure-doc-extraction-test-key \
    --secret-string '{"key":"your-azure-key"}' \
    --region us-west-2
```

## Summary

**Development Setup:**
```env
USE_AWS_SECRETS=false
OPENAI_API_KEY=sk-...
VISION_MODEL=o4-mini
```

**Production Setup:**
```env
USE_AWS_SECRETS=true
AWS_SECRET_NAME_OPENAI=openai-api-key
AWS_REGION=us-west-2
VISION_MODEL=o4-mini
```

---

**Benefits**: Secure, auditable, and easy to rotate keys without code changes!
