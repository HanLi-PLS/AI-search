#!/usr/bin/env python3
"""
Test web search stock price fetching using GPT-4
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.app.api.routes.stocks import (
    get_stock_data_from_websearch,
    get_stock_data,
    FALLBACK_HKEX_BIOTECH_COMPANIES
)

print("="*70)
print("WEB SEARCH STOCK PRICE TEST")
print("="*70)

# Check if OPENAI_API_KEY is set
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    print("\n❌ ERROR: OPENAI_API_KEY not set in environment")
    print("Set it with: export OPENAI_API_KEY='your-key-here'")
    sys.exit(1)

print(f"\n✓ OPENAI_API_KEY is set")

# Test with a few well-known HK biotech stocks
test_companies = FALLBACK_HKEX_BIOTECH_COMPANIES[:3]

print("\n" + "="*70)
print("TESTING WEB SEARCH DATA EXTRACTION")
print("="*70)
print("\nThis will use GPT-4 to search the web for current stock prices")

for company in test_companies:
    ticker = company['ticker']
    name = company['name']

    print(f"\n{ticker} - {name}")
    print(f"Searching...")

    result = get_stock_data_from_websearch(ticker, name=name)

    if result:
        print(f"  ✓ SUCCESS!")
        print(f"  ✓ Price: HKD {result['current_price']:.2f}")
        print(f"  ✓ Change: {result['change']:+.2f} ({result['change_percent']:+.2f}%)")
        if result.get('volume'):
            print(f"  ✓ Volume: {result['volume']:,}")
        print(f"  ✓ Data source: {result['data_source']}")
        print(f"  ✓ Last updated: {result['last_updated']}")
    else:
        print(f"  ✗ FAILED - Could not extract price from web search")

print("\n" + "="*70)
print("TESTING FULL MULTI-SOURCE get_stock_data()")
print("="*70)
print("\nThis will try: yfinance -> AKShare -> Web Search -> demo data")

for company in test_companies:
    ticker = company['ticker']
    code = company['code']
    name = company['name']

    print(f"\n{ticker} - {name}")
    result = get_stock_data(ticker, code=code, name=name, use_cache=False)

    if result:
        is_demo = "Demo Data" in result.get('data_source', '')
        is_websearch = "Web Search" in result.get('data_source', '')

        symbol = "✓" if not is_demo else "⚠"

        print(f"  {symbol} Price: HKD {result['current_price']:.2f}")
        print(f"  {symbol} Change: {result['change']:+.2f} ({result['change_percent']:+.2f}%)")
        print(f"  {symbol} Data source: {result['data_source']}")

        if is_websearch:
            print(f"  💡 Got real data from web search!")
        elif is_demo:
            print(f"  ⚠ Using demo data (all real sources failed)")
    else:
        print(f"  ✗ Completely failed")

print("\n" + "="*70)
print("SUMMARY")
print("="*70)

real_count = 0
websearch_count = 0
demo_count = 0

for company in test_companies:
    result = get_stock_data(company['ticker'], code=company['code'], name=company['name'], use_cache=True)
    if result:
        data_source = result.get('data_source', '')
        if "Demo Data" in data_source:
            demo_count += 1
        elif "Web Search" in data_source:
            websearch_count += 1
            real_count += 1
        else:
            real_count += 1

print(f"\nTotal tested: {len(test_companies)}")
print(f"Real data (API): {real_count - websearch_count}/{len(test_companies)}")
print(f"Real data (Web Search): {websearch_count}/{len(test_companies)}")
print(f"Demo data: {demo_count}/{len(test_companies)}")

if real_count == len(test_companies):
    print("\n✓ SUCCESS! All companies have real stock data")
    if websearch_count > 0:
        print(f"  💡 {websearch_count} companies using web search as fallback")
elif real_count > 0:
    print(f"\n⚠ PARTIAL SUCCESS: {real_count} companies have real data, {demo_count} using demo")
    if websearch_count > 0:
        print(f"  💡 Web search provided data for {websearch_count} companies")
else:
    print("\n✗ FAILURE: No real data available, all using demo data")

print("\n" + "="*70)
print("Note: Web search with GPT-4 incurs API costs")
print("Estimated cost per stock: ~$0.001-0.002 per lookup")
print("With 5-minute caching, cost is minimal for production use")
print("="*70)
