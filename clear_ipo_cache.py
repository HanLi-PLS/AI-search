#!/usr/bin/env python3
"""
Clear IPO cache and test the endpoint
"""
import sys
import requests
from pathlib import Path

# Test the IPO endpoint
print("=" * 60)
print("Testing IPO endpoint")
print("=" * 60)

# Test with force cache clear by adding a query parameter
backend_url = "http://44.233.7.216:8000/api/stocks/upcoming-ipos"

try:
    print(f"\nCalling: {backend_url}")
    response = requests.get(backend_url, timeout=10)

    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"\nResponse keys: {data.keys()}")
        print(f"Success: {data.get('success')}")
        print(f"Format: {data.get('format')}")

        if data.get('format') == 'html':
            print(f"HTML Content Length: {len(data.get('html_content', ''))} chars")
            print(f"HTML Preview: {data.get('html_content', '')[:200]}")
        elif data.get('format') == 'table':
            print(f"Record Count: {data.get('count')}")
            print(f"Columns: {data.get('columns')}")

        print(f"Source: {data.get('source')}")
    else:
        print(f"Error Response: {response.text}")

except requests.exceptions.Timeout:
    print("ERROR: Request timed out after 10 seconds")
except Exception as e:
    print(f"ERROR: {str(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("If still showing HTML format, the cache needs to be cleared")
print("Backend needs to be restarted to clear in-memory cache")
print("=" * 60)
