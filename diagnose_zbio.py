#!/usr/bin/env python3
"""
Diagnose ZBIO historical data fetching
"""
import tushare as ts
from datetime import datetime, timedelta
import os

# Set token from environment or config
token = os.getenv('TUSHARE_API_TOKEN')
if token:
    ts.set_token(token)
else:
    print("Warning: TUSHARE_API_TOKEN not set")

pro = ts.pro_api()

print("=" * 60)
print("Testing Tushare US Daily API for ZBIO")
print("=" * 60)
print()

ticker = "ZBIO"
end_date = datetime.now().strftime('%Y%m%d')
start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')

print(f"Ticker: {ticker}")
print(f"Start Date: {start_date}")
print(f"End Date: {end_date}")
print()

try:
    print("Calling pro.us_daily(ts_code='ZBIO', start_date=..., end_date=...)...")
    df = pro.us_daily(ts_code=ticker, start_date=start_date, end_date=end_date)

    print(f"Result: {type(df)}")
    print(f"Is None: {df is None}")
    print(f"Is Empty: {df.empty if df is not None else 'N/A'}")

    if df is not None and not df.empty:
        print(f"\n✓ SUCCESS: Got {len(df)} records")
        print("\nFirst few records:")
        print(df.head())
        print("\nColumns:")
        print(df.columns.tolist())
    else:
        print("\n✗ FAILED: No data returned")
        print("\nTrying with longer date range (90 days)...")

        start_date_90 = (datetime.now() - timedelta(days=90)).strftime('%Y%m%d')
        df2 = pro.us_daily(ts_code=ticker, start_date=start_date_90, end_date=end_date)

        if df2 is not None and not df2.empty:
            print(f"✓ Got {len(df2)} records with 90-day range")
            print(df2.head())
        else:
            print("✗ Still no data with 90-day range")

            # Try getting any recent US stock to verify API works
            print("\nTrying with AAPL (Apple) to verify API works...")
            df3 = pro.us_daily(ts_code='AAPL', start_date=start_date, end_date=end_date)
            if df3 is not None and not df3.empty:
                print(f"✓ AAPL works: Got {len(df3)} records")
                print("This means the API works but ZBIO might not be available")
            else:
                print("✗ AAPL also failed - API might have issues")

except Exception as e:
    print(f"\n✗ ERROR: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()

print()
print("=" * 60)
