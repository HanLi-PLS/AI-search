#!/usr/bin/env python3
"""
Test Finnhub API for ZBIO historical data
"""
import finnhub
import os
from datetime import datetime, timedelta

# Check if Finnhub API key is available
api_key = os.getenv('FINNHUB_API_KEY')
if not api_key:
    print("ERROR: FINNHUB_API_KEY environment variable not set")
    print("Trying to load from backend config...")

    try:
        import sys
        sys.path.insert(0, '/opt/ai-search')
        from backend.app.config import settings
        api_key = settings.FINNHUB_API_KEY
        if api_key:
            print(f"✓ Got API key from settings: {api_key[:10]}...")
        else:
            print("✗ No API key in settings either")
            exit(1)
    except Exception as e:
        print(f"✗ Could not load settings: {e}")
        exit(1)

print("=" * 60)
print("Testing Finnhub API for ZBIO Historical Data")
print("=" * 60)
print()

ticker = "ZBIO"
print(f"Ticker: {ticker}")
print(f"API Key: {api_key[:10]}..." if api_key else "No API key")
print()

try:
    # Create Finnhub client
    finnhub_client = finnhub.Client(api_key=api_key)

    # Test 1: Get current quote
    print("Test 1: Getting current quote...")
    quote = finnhub_client.quote(ticker)
    print(f"Quote response: {quote}")

    if quote.get('c'):
        print(f"✓ Current price: ${quote['c']}")
    else:
        print("✗ No current price in response")

    print()

    # Test 2: Get historical candles (last 30 days)
    print("Test 2: Getting historical candles (last 30 days)...")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    start_timestamp = int(start_date.timestamp())
    end_timestamp = int(end_date.timestamp())

    print(f"Start: {start_date.strftime('%Y-%m-%d')} ({start_timestamp})")
    print(f"End: {end_date.strftime('%Y-%m-%d')} ({end_timestamp})")
    print()

    res = finnhub_client.stock_candles(ticker, 'D', start_timestamp, end_timestamp)

    print(f"Candles response: {res}")
    print()

    if res.get('s') == 'ok':
        count = len(res.get('c', []))
        print(f"✓ SUCCESS: Got {count} candles")

        if count > 0:
            print(f"\nFirst candle:")
            print(f"  Date: {datetime.fromtimestamp(res['t'][0]).strftime('%Y-%m-%d')}")
            print(f"  Open: ${res['o'][0]}")
            print(f"  High: ${res['h'][0]}")
            print(f"  Low: ${res['l'][0]}")
            print(f"  Close: ${res['c'][0]}")
            print(f"  Volume: {res['v'][0]}")

            print(f"\nLast candle:")
            print(f"  Date: {datetime.fromtimestamp(res['t'][-1]).strftime('%Y-%m-%d')}")
            print(f"  Open: ${res['o'][-1]}")
            print(f"  High: ${res['h'][-1]}")
            print(f"  Low: ${res['l'][-1]}")
            print(f"  Close: ${res['c'][-1]}")
            print(f"  Volume: {res['v'][-1]}")
    else:
        print(f"✗ FAILED: Status = {res.get('s')}")

except Exception as e:
    print(f"\n✗ ERROR: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()

print()
print("=" * 60)
