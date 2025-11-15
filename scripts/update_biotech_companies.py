#!/usr/bin/env python3
"""
Script to update biotech company list from AAStocks or AKShare
Run this on EC2 to test if scraping works from that network location
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.app.api.routes.stocks import scrape_hkex_biotech_companies, get_hkex_biotech_companies
import json

def main():
    print("Testing AAStocks web scraping...")
    print("="*60)

    # Try scraping
    companies = scrape_hkex_biotech_companies()

    if companies:
        print(f"\n✓ SUCCESS! Scraped {len(companies)} companies from AAStocks\n")
        print("="*60)

        for company in companies:
            print(f"{company['code']:6s} | {company['ticker']:10s} | {company['name']}")

        print("="*60)
        print(f"\nTotal: {len(companies)} companies")

        # Save to file
        output_file = '/tmp/scraped_biotech_companies.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(companies, f, ensure_ascii=False, indent=2)
        print(f"\nSaved to {output_file}")

        # Generate Python code
        print("\n# Code to update backend/app/api/routes/stocks.py:")
        print("\nFALLBACK_HKEX_BIOTECH_COMPANIES = [")
        for company in companies:
            print(f'    {{"ticker": "{company["ticker"]}", "code": "{company["code"]}", "name": "{company["name"]}"}},')
        print("]")

    else:
        print("\n✗ Scraping failed (blocked with 403 or parsing error)")
        print("\nTrying to get companies using fallback...")

        companies = get_hkex_biotech_companies()
        print(f"Using fallback list: {len(companies)} companies")

    # Also try AKShare if available
    print("\n" + "="*60)
    print("Testing AKShare HK stock data...")
    print("="*60)

    try:
        import akshare as ak
        print("\nFetching HK stocks from AKShare...")
        df = ak.stock_hk_spot_em()
        print(f"✓ SUCCESS! Got {len(df)} HK stocks from AKShare")

        # Filter for biotech
        biotech_keywords = ['生物', '医药', '制药', 'Bio', 'Pharma']
        pattern = '|'.join(biotech_keywords)
        biotech_df = df[df['名称'].str.contains(pattern, case=False, na=False)]

        print(f"✓ Found {len(biotech_df)} biotech companies by keyword filter")
        print("\nTop 20 biotech companies:")
        for idx, row in biotech_df.head(20).iterrows():
            print(f"{row['代码']:6s} | {row['名称']:40s} | {row.get('最新价', 'N/A')}")

    except ImportError:
        print("✗ AKShare not installed")
    except Exception as e:
        print(f"✗ AKShare failed: {e}")

if __name__ == "__main__":
    main()
