#!/usr/bin/env python3
"""
Enhanced diagnostic to understand why only 30 companies are being scraped
when there should be 60+
"""

import requests
from bs4 import BeautifulSoup
import re

def diagnose_aastocks_page():
    """Detailed analysis of AAStocks page structure"""

    url = "https://www.aastocks.com/tc/stocks/market/topic/biotech"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Referer': 'https://www.aastocks.com/',
    }

    print("Fetching AAStocks biotech page...")
    print(f"URL: {url}\n")

    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Content length: {len(response.content)} bytes\n")

        if response.status_code != 200:
            print(f"Error: Got status {response.status_code}")
            return

        soup = BeautifulSoup(response.content, 'html.parser')

        # Save full HTML for inspection
        with open('/tmp/aastocks_full_page.html', 'w', encoding='utf-8') as f:
            f.write(soup.prettify())
        print("✓ Saved full HTML to /tmp/aastocks_full_page.html\n")

        # Find all tables
        tables = soup.find_all('table')
        print(f"Found {len(tables)} tables on the page\n")

        # Analyze each table
        for idx, table in enumerate(tables):
            rows = table.find_all('tr')
            print(f"Table {idx + 1}:")
            print(f"  Total rows: {len(rows)}")

            # Count rows with stock links
            stock_links = table.find_all('a', href=re.compile(r'/stocks/quote/detail-quote\.aspx\?symbol=\d{5}'))
            print(f"  Rows with stock codes: {len(stock_links)}")

            # Show table ID/class if any
            table_id = table.get('id', 'no-id')
            table_class = table.get('class', 'no-class')
            print(f"  Table ID: {table_id}")
            print(f"  Table class: {table_class}\n")

        # Look for pagination
        print("Checking for pagination...")
        pagination_patterns = [
            'pagination', 'pager', 'page-', 'nextpage',
            '下一頁', '上一頁', 'next', 'prev'
        ]

        found_pagination = False
        for pattern in pagination_patterns:
            elements = soup.find_all(text=re.compile(pattern, re.I))
            if elements:
                print(f"  Found pagination keyword: '{pattern}'")
                found_pagination = True

        # Check for pagination buttons/links
        page_links = soup.find_all('a', href=re.compile(r'page=\d+|p=\d+', re.I))
        if page_links:
            print(f"  Found {len(page_links)} pagination links")
            found_pagination = True

        if not found_pagination:
            print("  ✗ No pagination elements found\n")
        else:
            print()

        # Count all stock codes on page
        all_stock_links = soup.find_all('a', href=re.compile(r'/stocks/quote/detail-quote\.aspx\?symbol=\d{5}'))
        print(f"Total stock links found: {len(all_stock_links)}")

        # Extract all unique stock codes
        codes = set()
        for link in all_stock_links:
            ticker = link.get_text(strip=True)
            if ticker and '.HK' in ticker:
                code = ticker.replace('.HK', '')
                codes.add(code)

        print(f"Unique stock codes: {len(codes)}")
        print(f"\nCodes found: {sorted(codes)[:20]}...")

        # Check if there are tbody sections
        tbodies = soup.find_all('tbody')
        print(f"\nFound {len(tbodies)} <tbody> sections")
        for idx, tbody in enumerate(tbodies):
            rows = tbody.find_all('tr')
            print(f"  tbody {idx + 1}: {len(rows)} rows")

        # Look for JavaScript that might load more data
        scripts = soup.find_all('script')
        print(f"\nFound {len(scripts)} script tags")

        ajax_keywords = ['ajax', 'xhr', 'fetch', 'loadmore', 'getdata']
        for script in scripts:
            script_text = script.get_text()
            for keyword in ajax_keywords:
                if keyword.lower() in script_text.lower():
                    print(f"  ⚠ Found '{keyword}' in script - might indicate dynamic loading")
                    break

        print("\n" + "="*60)
        print(f"SUMMARY: Found {len(codes)} unique companies")
        print(f"Expected: 60+ companies")

        if len(codes) < 60:
            print(f"\n⚠ WARNING: Only found {len(codes)} companies, expected 60+")
            print("Possible reasons:")
            print("  - Data is loaded dynamically via JavaScript")
            print("  - Pagination exists but wasn't detected")
            print("  - Multiple pages need to be scraped")
            print("\nCheck /tmp/aastocks_full_page.html for more details")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    diagnose_aastocks_page()
