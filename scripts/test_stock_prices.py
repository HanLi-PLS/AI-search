#!/usr/bin/env python3
"""
Test stock price fetching to diagnose "Unable to fetch data" errors
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.app.api.routes.stocks import (
    get_stock_data,
    get_stock_data_from_akshare,
    get_demo_stock_data,
    AKSHARE_AVAILABLE,
    DEMO_STOCK_DATA,
    FALLBACK_HKEX_BIOTECH_COMPANIES
)

print("="*70)
print("STOCK PRICE FETCHING DIAGNOSTIC")
print("="*70)

print(f"\nAKShare available: {AKSHARE_AVAILABLE}")

if AKSHARE_AVAILABLE:
    print("✓ AKShare is installed")
    try:
        import akshare as ak
        print(f"  AKShare version: {ak.__version__}")

        # Test fetching HK spot data
        print("\nTesting AKShare HK spot data fetch...")
        df = ak.stock_hk_spot_em()
        print(f"✓ Successfully fetched {len(df)} HK stocks from AKShare")
        print(f"\nColumn names: {list(df.columns)}")
        print(f"\nFirst few stock codes: {list(df['代码'].head(10))}")

        # Check if our biotech companies are in the data
        print("\n" + "="*70)
        print("CHECKING BIOTECH COMPANIES IN AKSHARE DATA")
        print("="*70)

        test_companies = FALLBACK_HKEX_BIOTECH_COMPANIES[:5]  # Test first 5

        for company in test_companies:
            code = company['code']
            ticker = company['ticker']
            name = company['name']

            # Check if code exists in AKShare data
            stock_row = df[df['代码'] == code]

            if not stock_row.empty:
                row = stock_row.iloc[0]
                price = row.get('最新价', 'N/A')
                print(f"✓ {code} ({ticker}) - {name}: ¥{price}")
            else:
                print(f"✗ {code} ({ticker}) - {name}: NOT FOUND in AKShare data")

                # Try to find similar codes
                similar = df[df['代码'].str.contains(code[-4:], na=False)]
                if not similar.empty:
                    print(f"  Similar codes found: {list(similar['代码'].head(3))}")

        # Test the actual function
        print("\n" + "="*70)
        print("TESTING get_stock_data_from_akshare() FUNCTION")
        print("="*70)

        for company in test_companies:
            code = company['code']
            ticker = company['ticker']
            name = company['name']

            print(f"\nTesting {ticker} ({code})...")
            result = get_stock_data_from_akshare(code, ticker)

            if result:
                print(f"✓ Success! Price: {result.get('current_price')}, Change: {result.get('change')}")
            else:
                print(f"✗ Failed to fetch data")

    except Exception as e:
        print(f"✗ AKShare test failed: {e}")
        import traceback
        traceback.print_exc()
else:
    print("✗ AKShare is NOT installed")

# Check demo data
print("\n" + "="*70)
print("DEMO DATA AVAILABILITY")
print("="*70)

print(f"\nTotal tickers in DEMO_STOCK_DATA: {len(DEMO_STOCK_DATA)}")
print(f"Demo data tickers: {list(DEMO_STOCK_DATA.keys())}")

# Check how many of our companies have demo data
companies_with_demo = 0
for company in FALLBACK_HKEX_BIOTECH_COMPANIES:
    if company['ticker'] in DEMO_STOCK_DATA:
        companies_with_demo += 1

print(f"\nBiotech companies with demo data: {companies_with_demo}/{len(FALLBACK_HKEX_BIOTECH_COMPANIES)}")

if companies_with_demo < len(FALLBACK_HKEX_BIOTECH_COMPANIES):
    print(f"⚠ {len(FALLBACK_HKEX_BIOTECH_COMPANIES) - companies_with_demo} companies have NO demo data fallback")

# Test get_stock_data function
print("\n" + "="*70)
print("TESTING get_stock_data() FUNCTION (with fallback)")
print("="*70)

test_companies = FALLBACK_HKEX_BIOTECH_COMPANIES[:3]

for company in test_companies:
    ticker = company['ticker']
    code = company['code']
    name = company['name']

    print(f"\n{ticker} ({code}) - {name}")
    result = get_stock_data(ticker, code=code, use_cache=False)

    if result:
        print(f"  ✓ Data source: {result.get('data_source')}")
        print(f"  ✓ Price: {result.get('current_price')}")
    else:
        print(f"  ✗ Returned None (will show 'Unable to fetch data' in frontend)")

print("\n" + "="*70)
print("SUMMARY")
print("="*70)

if not AKSHARE_AVAILABLE:
    print("❌ CRITICAL: AKShare not installed - no live data available")
    print("   Install with: pip install akshare")
elif companies_with_demo < len(FALLBACK_HKEX_BIOTECH_COMPANIES):
    print(f"⚠ WARNING: Only {companies_with_demo}/{len(FALLBACK_HKEX_BIOTECH_COMPANIES)} companies have demo data")
    print("   Most companies will show 'Unable to fetch data' if AKShare fails")
    print("   Consider expanding DEMO_STOCK_DATA to cover all 66 companies")
