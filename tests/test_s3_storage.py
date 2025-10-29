#!/usr/bin/env python3
"""
Test S3 Storage integration

This script tests the ability to upload, download, and delete files from S3.
Run this to verify your S3 configuration.

Usage:
    python tests/test_s3_storage.py
"""

import sys
from pathlib import Path
import tempfile

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.utils.s3_storage import S3Storage
from botocore.exceptions import ClientError
import boto3


def test_aws_credentials():
    """Test if AWS credentials are configured"""
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
        return False


def test_bucket_exists(bucket_name: str, region_name: str):
    """Test if S3 bucket exists and is accessible"""
    print(f"\nTesting S3 bucket access: {bucket_name}...")
    try:
        s3 = boto3.client('s3', region_name=region_name)
        s3.head_bucket(Bucket=bucket_name)
        print(f"✅ Bucket '{bucket_name}' exists and is accessible")
        return True
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            print(f"❌ Bucket '{bucket_name}' does not exist")
            print(f"\n   To create the bucket:")
            print(f"   aws s3 mb s3://{bucket_name} --region {region_name}")
        elif error_code == '403':
            print(f"❌ Access denied to bucket '{bucket_name}'")
            print(f"\n   Required IAM permissions:")
            print("   - s3:PutObject")
            print("   - s3:GetObject")
            print("   - s3:DeleteObject")
            print("   - s3:ListBucket")
        else:
            print(f"❌ Error accessing bucket: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False


def test_upload_download_delete(bucket_name: str, region_name: str):
    """Test upload, download, and delete operations"""
    print(f"\nTesting S3 operations...")

    try:
        storage = S3Storage(bucket_name, region_name)

        # Create a test file
        test_content = b"Hello from AI Document Search Test!"
        test_key = "test/test_file.txt"

        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp_file:
            tmp_file.write(test_content)
            tmp_file_path = Path(tmp_file.name)

        # Test 1: Upload
        print("   Testing upload...")
        if not storage.upload_file(tmp_file_path, test_key):
            print("   ❌ Upload failed")
            return False
        print("   ✅ Upload successful")

        # Test 2: File exists
        print("   Testing file existence check...")
        if not storage.file_exists(test_key):
            print("   ❌ File existence check failed")
            return False
        print("   ✅ File exists")

        # Test 3: Get file size
        print("   Testing get file size...")
        file_size = storage.get_file_size(test_key)
        if file_size != len(test_content):
            print(f"   ❌ File size mismatch: expected {len(test_content)}, got {file_size}")
            return False
        print(f"   ✅ File size correct: {file_size} bytes")

        # Test 4: Download
        print("   Testing download...")
        download_path = Path(tempfile.gettempdir()) / "downloaded_test.txt"
        if not storage.download_file(test_key, download_path):
            print("   ❌ Download failed")
            return False

        with open(download_path, 'rb') as f:
            downloaded_content = f.read()

        if downloaded_content != test_content:
            print("   ❌ Downloaded content doesn't match")
            return False
        print("   ✅ Download successful")

        # Test 5: List files
        print("   Testing list files...")
        files = storage.list_files(prefix="test/")
        if test_key not in files:
            print("   ❌ Uploaded file not in list")
            return False
        print(f"   ✅ List files successful ({len(files)} file(s) found)")

        # Test 6: Generate presigned URL
        print("   Testing presigned URL generation...")
        url = storage.get_presigned_url(test_key, expiration=60)
        if not url or not url.startswith('https://'):
            print("   ❌ Presigned URL generation failed")
            return False
        print("   ✅ Presigned URL generated")

        # Test 7: Delete
        print("   Testing delete...")
        if not storage.delete_file(test_key):
            print("   ❌ Delete failed")
            return False
        print("   ✅ Delete successful")

        # Test 8: Verify deletion
        print("   Testing file no longer exists...")
        if storage.file_exists(test_key):
            print("   ❌ File still exists after deletion")
            return False
        print("   ✅ File successfully deleted")

        # Cleanup
        tmp_file_path.unlink()
        if download_path.exists():
            download_path.unlink()

        print("\n✅ All S3 operations successful")
        return True

    except Exception as e:
        print(f"\n❌ S3 operations test failed: {str(e)}")
        return False


def test_bucket_permissions(bucket_name: str, region_name: str):
    """Test bucket permissions"""
    print(f"\nTesting S3 bucket permissions...")

    s3 = boto3.client('s3', region_name=region_name)
    permissions_ok = True

    # Test ListBucket
    try:
        s3.list_objects_v2(Bucket=bucket_name, MaxKeys=1)
        print("   ✅ s3:ListBucket - OK")
    except Exception as e:
        print(f"   ❌ s3:ListBucket - FAILED: {str(e)}")
        permissions_ok = False

    # PutObject, GetObject, DeleteObject are tested in test_upload_download_delete
    return permissions_ok


def main():
    """Run all tests"""
    bucket_name = "plfs-han-ai-search"
    region_name = "us-west-2"

    print("=" * 60)
    print("S3 Storage Integration Test")
    print("=" * 60)
    print(f"Bucket: {bucket_name}")
    print(f"Region: {region_name}")
    print("=" * 60)

    results = []

    # Test 1: AWS credentials
    results.append(("AWS Credentials", test_aws_credentials()))

    # Test 2: Bucket exists
    if results[0][1]:
        results.append(("Bucket Access", test_bucket_exists(bucket_name, region_name)))

    # Test 3: Bucket permissions
    if len(results) == 2 and results[1][1]:
        results.append(("Bucket Permissions", test_bucket_permissions(bucket_name, region_name)))

    # Test 4: Upload/Download/Delete
    if len(results) == 3 and results[2][1]:
        results.append(("S3 Operations", test_upload_download_delete(bucket_name, region_name)))

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
        print("🎉 All tests passed! S3 storage is configured correctly.")
        print("\nYou can now set in .env:")
        print("  USE_S3_STORAGE=true")
        print(f"  AWS_S3_BUCKET={bucket_name}")
        print(f"  AWS_REGION={region_name}")
        print("  S3_UPLOAD_PREFIX=uploads/")
        print("\nUploaded files will be stored in S3 instead of local disk.")
    else:
        print("❌ Some tests failed. Please fix the issues above.")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
