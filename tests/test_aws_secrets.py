#!/usr/bin/env python3
"""
Test AWS Secrets Manager integration

This script tests the ability to retrieve secrets from AWS Secrets Manager.
Run this to verify your AWS credentials and Secrets Manager setup.

Usage:
    python tests/test_aws_secrets.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.utils.aws_secrets import get_key
from botocore.exceptions import ClientError


def test_aws_credentials():
    """Test if AWS credentials are configured"""
    import boto3

    print("Testing AWS credentials...")
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print(f"✅ AWS credentials configured")
        print(f"   Account: {identity['Account']}")
        print(f"   User ARN: {identity['Arn']}")
        return True
    except Exception as e:
        print(f"❌ AWS credentials not configured: {str(e)}")
        print("\nTo configure AWS credentials:")
        print("  1. Run: aws configure")
        print("  2. Or set environment variables:")
        print("     export AWS_ACCESS_KEY_ID=...")
        print("     export AWS_SECRET_ACCESS_KEY=...")
        print("     export AWS_REGION=us-west-2")
        return False


def test_secrets_manager_access():
    """Test if Secrets Manager is accessible"""
    import boto3

    print("\nTesting Secrets Manager access...")
    try:
        client = boto3.client('secretsmanager', region_name='us-west-2')
        response = client.list_secrets(MaxResults=1)
        print(f"✅ Secrets Manager accessible")
        return True
    except Exception as e:
        print(f"❌ Cannot access Secrets Manager: {str(e)}")
        return False


def test_openai_secret():
    """Test retrieving OpenAI API key from Secrets Manager"""
    print("\nTesting OpenAI API key retrieval...")

    secret_name = "openai-api-key"
    region_name = "us-west-2"

    try:
        api_key = get_key(secret_name, region_name)

        # Check if key looks valid (starts with sk-)
        if api_key.startswith('sk-'):
            print(f"✅ OpenAI API key retrieved successfully")
            print(f"   Secret name: {secret_name}")
            print(f"   Region: {region_name}")
            print(f"   Key preview: {api_key[:15]}...")
            return True
        else:
            print(f"⚠️  Retrieved key but format may be incorrect")
            print(f"   Expected to start with 'sk-' but got: {api_key[:10]}...")
            return False

    except ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"❌ Failed to retrieve secret: {error_code}")

        if error_code == 'ResourceNotFoundException':
            print(f"\n   Secret '{secret_name}' not found in {region_name}")
            print("\n   To create the secret:")
            print(f"   aws secretsmanager create-secret \\")
            print(f"       --name {secret_name} \\")
            print(f"       --description 'OpenAI API key for AI Document Search' \\")
            print(f"       --secret-string '{{\"key\":\"your-openai-api-key-here\"}}' \\")
            print(f"       --region {region_name}")
        elif error_code == 'AccessDeniedException':
            print(f"\n   Access denied to secret '{secret_name}'")
            print("\n   Required IAM permissions:")
            print("   - secretsmanager:GetSecretValue")
            print("   - secretsmanager:DescribeSecret")
        else:
            print(f"\n   Error: {e}")

        return False

    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False


def test_list_secrets():
    """List all available secrets"""
    import boto3

    print("\nListing available secrets...")
    try:
        client = boto3.client('secretsmanager', region_name='us-west-2')
        response = client.list_secrets(MaxResults=10)

        if not response.get('SecretList'):
            print("   No secrets found in us-west-2")
            return True

        print(f"   Found {len(response['SecretList'])} secret(s):")
        for secret in response['SecretList']:
            print(f"   - {secret['Name']}")

        return True

    except Exception as e:
        print(f"❌ Failed to list secrets: {str(e)}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("AWS Secrets Manager Integration Test")
    print("=" * 60)

    results = []

    # Test 1: AWS credentials
    results.append(("AWS Credentials", test_aws_credentials()))

    # Test 2: Secrets Manager access
    if results[0][1]:  # Only if credentials work
        results.append(("Secrets Manager Access", test_secrets_manager_access()))

    # Test 3: List secrets
    if len(results) == 2 and results[1][1]:
        results.append(("List Secrets", test_list_secrets()))

    # Test 4: OpenAI secret
    if len(results) == 3 and results[2][1]:
        results.append(("OpenAI Secret", test_openai_secret()))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    all_passed = all(result for _, result in results)

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All tests passed! AWS Secrets Manager is configured correctly.")
        print("\nYou can now set in .env:")
        print("  USE_AWS_SECRETS=true")
        print("  AWS_SECRET_NAME_OPENAI=openai-api-key")
        print("  AWS_REGION=us-west-2")
    else:
        print("❌ Some tests failed. Please fix the issues above.")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
