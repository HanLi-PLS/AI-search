#!/usr/bin/env python3
"""
Extract JavaScript from the HTML file
"""
import boto3
import re

# Create S3 client
s3_client = boto3.client('s3', region_name='us-west-2')

# Read the HTML file
html_key = "public_company_tracker/hkex_ipo_tracker/hkex_ipo_report_20251116_222848.html"
bucket_name = "plfs-han-ai-search"

response = s3_client.get_object(Bucket=bucket_name, Key=html_key)
html_content = response['Body'].read().decode('utf-8')

# Extract the <script> section
script_match = re.search(r'<script>(.*?)</script>', html_content, re.DOTALL)

if script_match:
    js_content = script_match.group(1)
    print("=" * 80)
    print("JavaScript from Original HTML File")
    print("=" * 80)
    print(js_content)
    print("\n" + "=" * 80)
else:
    print("No <script> section found in HTML")
