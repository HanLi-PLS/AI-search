#!/usr/bin/env python3
"""
Check the latest data available from Tushare and in our database
"""
import sys
import os
from datetime import datetime, date

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.app.services.stock_data import StockDataService
from backend.app.config import settings
import tushare as ts

def check_latest_data():
    """Check latest data from Tushare and database"""

    print(f"Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Today's Date: {date.today()}")
    print("=" * 70)

    # Initialize Tushare
    if settings.TUSHARE_API_TOKEN:
        ts.set_token(settings.TUSHARE_API_TOKEN)
        pro = ts.pro_api()
        print("✓ Tushare API initialized")
    else:
        print("✗ Tushare API token not available")
        return

    print("\n1. Checking Tushare API for latest available data...")
    print("-" * 70)

    # Check a sample stock (e.g., 02561.HK - 维升药业)
    sample_ticker = "02561.HK"

    try:
        # Fetch latest data from Tushare
        df = pro.hk_daily(ts_code=sample_ticker, start_date=None, end_date=None)

        if df is not None and not df.empty:
            latest_tushare = df.iloc[0]
            print(f"Sample Stock: {sample_ticker}")
            print(f"Latest Date in Tushare: {latest_tushare['trade_date']}")
            print(f"Close Price: {latest_tushare['close']}")
            print(f"Volume: {latest_tushare['vol']}")

            # Parse the date
            tushare_date = datetime.strptime(latest_tushare['trade_date'], '%Y%m%d').date()
            print(f"Parsed Date: {tushare_date}")

            if tushare_date == date.today():
                print("✓ TODAY'S DATA IS AVAILABLE in Tushare!")
            else:
                print(f"ℹ Latest data is from {tushare_date} (not today)")
        else:
            print("✗ No data returned from Tushare")

    except Exception as e:
        print(f"✗ Error fetching from Tushare: {str(e)}")

    print("\n2. Checking Database for latest stored data...")
    print("-" * 70)

    # Check database
    service = StockDataService()

    try:
        # Get latest data from database
        latest_db = service.get_historical_data(ticker=sample_ticker, limit=1)

        if latest_db:
            latest_record = latest_db[0]
            print(f"Sample Stock: {sample_ticker}")
            print(f"Latest Date in Database: {latest_record['trade_date']}")
            print(f"Close Price: {latest_record['close']}")

            # Parse the date
            db_date = datetime.fromisoformat(latest_record['trade_date']).date()

            if db_date == date.today():
                print("✓ TODAY'S DATA IS IN DATABASE!")
            else:
                print(f"ℹ Latest data in DB is from {db_date}")
                print(f"⚠ Database needs update! Run: POST /api/stocks/bulk-update-history")
        else:
            print("✗ No data found in database")

    except Exception as e:
        print(f"✗ Error checking database: {str(e)}")

    print("\n3. Recommendation:")
    print("-" * 70)
    print("If today's data is available in Tushare but not in the database,")
    print("trigger an update by calling:")
    print("  curl -X POST http://localhost:8000/api/stocks/bulk-update-history")
    print("=" * 70)

if __name__ == "__main__":
    check_latest_data()
