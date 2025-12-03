#!/usr/bin/env python3
"""
Restore historical data from S3 back to SQLite
Use this if data was archived to S3 but charts aren't showing it
"""
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.app.services.s3_storage import S3StockDataService
from backend.app.api.routes.stocks import get_hkex_biotech_companies
from backend.app.services.portfolio import PORTFOLIO_COMPANIES
from backend.app.database import get_session_local
from backend.app.models.stock import StockDaily
from datetime import datetime, date
from sqlalchemy import and_
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def restore_from_s3(ticker: str, ts_code: str):
    """
    Restore historical data from S3 back to SQLite

    Args:
        ticker: Stock ticker
        ts_code: Tushare code
    """
    try:
        s3_service = S3StockDataService()
        session_local = get_session_local()
        db = session_local()

        try:
            # Check what's in S3
            # Fetch last 2 years from S3
            end_date = date.today()
            start_date = date(end_date.year - 2, end_date.month, end_date.day)

            print(f"  Checking S3 for data from {start_date} to {end_date}...")
            s3_data = s3_service.load_from_s3(ticker, start_date, end_date)

            if not s3_data:
                print(f"  - No data found in S3")
                return 0

            print(f"  Found {len(s3_data)} records in S3")

            # Restore to SQLite
            restored = 0
            skipped = 0

            for record in s3_data:
                trade_date = datetime.fromisoformat(record['trade_date']).date()

                # Check if already exists
                existing = db.query(StockDaily).filter(
                    and_(
                        StockDaily.ticker == ticker,
                        StockDaily.trade_date == trade_date
                    )
                ).first()

                if existing:
                    skipped += 1
                    continue

                # Create new record
                stock_daily = StockDaily(
                    ticker=ticker,
                    ts_code=ts_code,
                    trade_date=trade_date,
                    open=record.get('open'),
                    high=record.get('high'),
                    low=record.get('low'),
                    close=record['close'],
                    pre_close=record.get('pre_close'),
                    volume=record.get('volume'),
                    amount=record.get('amount'),
                    change=record.get('change'),
                    pct_change=record.get('pct_change'),
                    data_source=record.get('data_source', 'S3 Restore')
                )
                db.add(stock_daily)
                restored += 1

            if restored > 0:
                db.commit()
                print(f"  ✓ Restored {restored} records from S3 (skipped {skipped} duplicates)")
            else:
                print(f"  - All records already in SQLite (skipped {skipped})")

            return restored

        finally:
            db.close()

    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
        logger.error(f"Error restoring {ticker}: {str(e)}")
        return 0


def main():
    """Restore all historical data from S3 back to SQLite"""
    print("=" * 70)
    print("Restore Historical Data from S3 to SQLite")
    print("=" * 70)
    print()
    print("This script will:")
    print("  1. Check S3 for archived historical data")
    print("  2. Restore it back to SQLite database")
    print("  3. Make charts show full historical data again")
    print()
    print("Note: This is safe - won't create duplicates")
    print()

    response = input("Continue? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Aborted.")
        return

    print()

    # Check S3 accessibility
    print("Testing S3 access...")
    try:
        s3_service = S3StockDataService()
        hkex_tickers = s3_service.list_archived_tickers(is_hkex=True)
        portfolio_tickers = s3_service.list_archived_tickers(is_hkex=False)
        print(f"✓ S3 accessible")
        print(f"  HKEX tickers in S3: {len(hkex_tickers)}")
        print(f"  Portfolio tickers in S3: {len(portfolio_tickers)}")
        print()

        if len(hkex_tickers) == 0 and len(portfolio_tickers) == 0:
            print("⚠️  No data found in S3!")
            print("   The data may not have been archived yet, or S3 paths may be wrong.")
            print()
            return

    except Exception as e:
        print(f"✗ Cannot access S3: {str(e)}")
        print()
        return

    # Restore HKEX 18A companies
    print("=" * 70)
    print("Restoring HKEX 18A Companies")
    print("=" * 70)
    print()

    try:
        companies = get_hkex_biotech_companies()
        total_restored = 0

        for i, company in enumerate(companies, 1):
            ticker = company['ticker']
            code = company.get('code')
            name = company['name']

            # Convert to Tushare format
            if code:
                ts_code = f"{code}.HK"
            else:
                stock_code = ticker.split('.')[0]
                ts_code = f"{stock_code.zfill(5)}.HK"

            print(f"[{i}/{len(companies)}] {ticker} - {name}")
            restored = restore_from_s3(ticker, ts_code)
            total_restored += restored
            print()

        print(f"HKEX 18A Summary: Restored {total_restored} total records")
        print()

    except Exception as e:
        logger.error(f"Error processing HKEX companies: {str(e)}")
        print(f"Error: {str(e)}")
        print()

    # Restore Portfolio companies
    print("=" * 70)
    print("Restoring Portfolio Companies")
    print("=" * 70)
    print()

    try:
        total_restored = 0

        for i, company in enumerate(PORTFOLIO_COMPANIES, 1):
            ticker = company['ticker']
            ts_code = company['ts_code']
            name = company['name']

            print(f"[{i}/{len(PORTFOLIO_COMPANIES)}] {ticker} - {name}")
            restored = restore_from_s3(ticker, ts_code)
            total_restored += restored
            print()

        print(f"Portfolio Summary: Restored {total_restored} total records")
        print()

    except Exception as e:
        logger.error(f"Error processing Portfolio companies: {str(e)}")
        print(f"Error: {str(e)}")
        print()

    # Final summary
    print("=" * 70)
    print("Restore Complete")
    print("=" * 70)
    print()
    print("Historical data has been restored from S3 to SQLite.")
    print("Charts should now show full historical data again.")
    print()
    print("Next steps:")
    print("  1. Refresh the Stock Tracker page")
    print("  2. Check if charts show full year of data")
    print()
    print("To prevent this in the future:")
    print("  - The S3 archival scheduler has been disabled")
    print("  - Only run manual archival after testing S3 retrieval")
    print()


if __name__ == "__main__":
    main()
