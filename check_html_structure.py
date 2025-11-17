#!/usr/bin/env python3
"""
Check HTML table structure to understand why sorting might not work
"""
import boto3
import re
from bs4 import BeautifulSoup

# Create S3 client
s3_client = boto3.client('s3', region_name='us-west-2')

# Read the HTML file
html_key = "public_company_tracker/hkex_ipo_tracker/hkex_ipo_report_20251116_222848.html"
bucket_name = "plfs-han-ai-search"

response = s3_client.get_object(Bucket=bucket_name, Key=html_key)
html_content = response['Body'].read().decode('utf-8')

print("=" * 80)
print("HTML Table Structure Analysis")
print("=" * 80)

# Parse HTML
soup = BeautifulSoup(html_content, 'html.parser')

# Find all tables
tables = soup.find_all('table')
print(f"\nFound {len(tables)} table(s) in the HTML")

for i, table in enumerate(tables):
    print(f"\n--- Table {i} ---")

    # Check for thead
    thead = table.find('thead')
    if thead:
        headers = thead.find_all('th')
        print(f"  Has <thead>: Yes")
        print(f"  Number of headers: {len(headers)}")
        print(f"  Header texts: {[h.get_text(strip=True)[:30] for h in headers[:5]]}")
    else:
        print(f"  Has <thead>: No")
        # Check if th in tbody or directly in table
        all_ths = table.find_all('th')
        print(f"  Total <th> tags: {len(all_ths)}")

    # Check for tbody
    tbody = table.find('tbody')
    if tbody:
        rows = tbody.find_all('tr')
        print(f"  Has <tbody>: Yes")
        print(f"  Number of rows: {len(rows)}")
    else:
        print(f"  Has <tbody>: No")
        all_trs = table.find_all('tr')
        print(f"  Total <tr> tags: {len(all_trs)}")

# Check if there's any embedded JavaScript
script_tags = soup.find_all('script')
print(f"\n\nFound {len(script_tags)} <script> tag(s)")
if script_tags:
    for i, script in enumerate(script_tags):
        content = script.string or script.get_text()
        if content:
            print(f"\nScript {i} (first 200 chars):")
            print(content[:200])

print("\n" + "=" * 80)
