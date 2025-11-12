#!/usr/bin/env python3
"""
Test real stock data fetching from yfinance and AKShare
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.app.api.routes.stocks import (
    get_stock_data,
    get_stock_data_from_yfinance,
    get_stock_data_from_akshare,
    YFINANCE_AVAILABLE,
    AKSHARE_AVAILABLE,
    FALLBACK_HKEX_BIOTECH_COMPANIES
)

print("="*70)
print("REAL STOCK DATA TESTING")
print("="*70)

print(f"\nyfinance available: {YFINANCE_AVAILABLE}")
print(f"AKShare available: {AKSHARE_AVAILABLE}")

if not YFINANCE_AVAILABLE and not AKSHARE_AVAILABLE:
    print("\n❌ ERROR: No real data sources available!")
    print("Install with: pip install yfinance akshare")
    sys.exit(1)

# Test with first 5 companies
test_companies = FALLBACK_HKEX_BIOTECH_COMPANIES[:5]

print("\n" + "="*70)
print("TESTING YFINANCE")
print("="*70)

if YFINANCE_AVAILABLE:
    for company in test_companies:
        ticker = company['ticker']
        name = company['name']

        print(f"\n{ticker} - {name}")
        result = get_stock_data_from_yfinance(ticker)

        if result:
            print(f"  ✓ Price: HKD {result['current_price']:.2f}")
            print(f"  ✓ Change: {result['change']:+.2f} ({result['change_percent']:+.2f}%)")
            print(f"  ✓ Volume: {result['volume']:,}")
            print(f"  ✓ Data source: {result['data_source']}")
        else:
            print(f"  ✗ Failed to fetch from yfinance")
else:
    print("⚠ yfinance not installed")

print("\n" + "="*70)
print("TESTING AKSHARE")
print("="*70)

if AKSHARE_AVAILABLE:
    for company in test_companies:
        ticker = company['ticker']
        code = company['code']
        name = company['name']

        print(f"\n{ticker} ({code}) - {name}")
        result = get_stock_data_from_akshare(code, ticker, retry_count=1)

        if result:
            print(f"  ✓ Price: HKD {result['current_price']:.2f}")
            print(f"  ✓ Change: {result['change']:+.2f} ({result['change_percent']:+.2f}%)")
            print(f"  ✓ Volume: {result['volume']:,}")
            print(f"  ✓ Data source: {result['data_source']}")
        else:
            print(f"  ✗ Failed to fetch from AKShare")
else:
    print("⚠ AKShare not installed")

print("\n" + "="*70)
print("TESTING MULTI-SOURCE get_stock_data()")
print("="*70)

print("\nThis will try yfinance first, then AKShare, then demo data as fallback")

for company in test_companies:
    ticker = company['ticker']
    code = company['code']
    name = company['name']

    print(f"\n{ticker} - {name}")
    result = get_stock_data(ticker, code=code, use_cache=False)

    if result:
        is_demo = "Demo Data" in result.get('data_source', '')
        symbol = "⚠" if is_demo else "✓"
        print(f"  {symbol} Price: HKD {result['current_price']:.2f}")
        print(f"  {symbol} Change: {result['change']:+.2f} ({result['change_percent']:+.2f}%)")
        print(f"  {symbol} Data source: {result['data_source']}")
    else:
        print(f"  ✗ Completely failed")

print("\n" + "="*70)
print("SUMMARY")
print("="*70)

success_count = 0
demo_count = 0

for company in test_companies:
    result = get_stock_data(company['ticker'], code=company['code'], use_cache=True)
    if result:
        if "Demo Data" in result.get('data_source', ''):
            demo_count += 1
        else:
            success_count += 1

print(f"\nReal data: {success_count}/{len(test_companies)}")
print(f"Demo data: {demo_count}/{len(test_companies)}")

if success_count == len(test_companies):
    print("\n✓ SUCCESS! All companies have real stock data")
elif success_count > 0:
    print(f"\n⚠ PARTIAL SUCCESS: {success_count} companies have real data, {demo_count} using demo")
else:
    print("\n✗ FAILURE: No real data available, all using demo data")
    print("\nPossible causes:")
    print("  - Network connectivity issues")
    print("  - API rate limiting")
    print("  - Data source blocking your IP")
    print("  - Need to run from different network (e.g., EC2)")
