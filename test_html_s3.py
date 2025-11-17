#!/usr/bin/env python3
"""
Test script to diagnose HTML file access in S3
"""
import sys
import boto3
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.services.ipo_data import IPODataService

def test_html_access():
    """Test if we can access the HTML file in S3"""
    service = IPODataService()

    # Test 1: List files in S3
    print("=" * 60)
    print("Test 1: List files in S3 IPO tracker folder")
    print("=" * 60)
    try:
        response = service.s3_client.list_objects_v2(
            Bucket=service.bucket_name,
            Prefix="public_company_tracker/hkex_ipo_tracker/"
        )

        if 'Contents' in response:
            print(f"\nFound {len(response['Contents'])} files:")
            for obj in sorted(response['Contents'], key=lambda x: x['LastModified'], reverse=True)[:10]:
                size_mb = obj['Size'] / (1024 * 1024)
                print(f"  {obj['Key']}")
                print(f"    Size: {size_mb:.2f} MB")
                print(f"    Last Modified: {obj['LastModified']}")
        else:
            print("No files found!")
    except Exception as e:
        print(f"ERROR: {str(e)}")

    # Test 2: Try to read the specific HTML file
    print("\n" + "=" * 60)
    print("Test 2: Read specific HTML file")
    print("=" * 60)
    html_key = "public_company_tracker/hkex_ipo_tracker/hkex_ipo_report_20251116_222848.html"
    try:
        print(f"\nAttempting to read: {html_key}")
        html_content = service.read_html_from_s3(html_key)
        print(f"SUCCESS! Read {len(html_content)} characters")
        print(f"First 200 chars: {html_content[:200]}")
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

    # Test 3: Try to read CSV file for comparison
    print("\n" + "=" * 60)
    print("Test 3: Read CSV file for comparison")
    print("=" * 60)
    csv_key = "public_company_tracker/hkex_ipo_tracker/hkex_ipo_2025_v20251113.csv"
    try:
        print(f"\nAttempting to read: {csv_key}")
        df = service.read_ipo_tracker_from_s3(csv_key)
        print(f"SUCCESS! Read {len(df)} rows")
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

    # Test 4: Test get_latest_ipo_file method
    print("\n" + "=" * 60)
    print("Test 4: Test get_latest_ipo_file method")
    print("=" * 60)
    try:
        latest = service.get_latest_ipo_file(prefer_html=True)
        print(f"Latest file (HTML preferred): {latest}")

        latest_csv = service.get_latest_ipo_file(prefer_html=False)
        print(f"Latest file (CSV preferred): {latest_csv}")
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_html_access()
