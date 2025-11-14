#!/usr/bin/env python3
"""
Script to ensure all stocks have full 1-year historical data
Checks current coverage and backfills as needed
"""
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.app.services.stock_data import StockDataService
from backend.app.api.routes.stocks import get_hkex_biotech_companies
from backend.app.services.portfolio import PORTFOLIO_COMPANIES
from backend.app.database import get_session_local
from backend.app.models.stock import StockDaily
from sqlalchemy import func
from datetime import date, timedelta
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_and_backfill(ticker: str, ts_code: str, target_days: int = 365):
    """
    Check historical data coverage and backfill if needed

    Args:
        ticker: Stock ticker
        ts_code: Tushare code
        target_days: Target number of days of history (default: 365)
    """
    session_local = get_session_local()
    db = session_local()
    service = StockDataService()

    try:
        # Get current data range
        earliest = db.query(func.min(StockDaily.trade_date)).filter(
            StockDaily.ticker == ticker
        ).scalar()

        latest = db.query(func.max(StockDaily.trade_date)).filter(
            StockDaily.ticker == ticker
        ).scalar()

        record_count = db.query(func.count(StockDaily.id)).filter(
            StockDaily.ticker == ticker
        ).scalar()

        if not earliest or not latest:
            print(f"  No data found - fetching initial {target_days} days...")

            # Fetch initial data
            end_date = date.today().strftime('%Y%m%d')
            start_date = (date.today() - timedelta(days=target_days)).strftime('%Y%m%d')

            new_records = service.fetch_and_store_historical_data(
                ticker=ticker,
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
                db=db
            )

            if new_records > 0:
                print(f"  ✓ Fetched {new_records} records")
            else:
                print(f"  ✗ No data available from API")

            return new_records

        # Calculate days of coverage
        days_covered = (latest - earliest).days
        target_start = date.today() - timedelta(days=target_days)

        print(f"  Current: {record_count} records ({earliest} to {latest}, {days_covered} days)")

        # Check if we need more data
        if earliest > target_start:
            days_needed = (earliest - target_start).days
            print(f"  Need {days_needed} more days to reach {target_days}-day target...")

            # Backfill older data
            new_records = service.backfill_historical_data(
                ticker=ticker,
                ts_code=ts_code,
                days=days_needed + 30,  # Add buffer for weekends/holidays
                db=db
            )

            if new_records > 0:
                print(f"  ✓ Backfilled {new_records} records")
            else:
                print(f"  - No older data available (may be newly listed)")

            return new_records
        else:
            print(f"  ✓ Already has {target_days}+ days of data")
            return 0

    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
        logger.error(f"Error processing {ticker}: {str(e)}")
        return 0
    finally:
        db.close()


def main():
    """Ensure all stocks have 1 year of historical data"""
    print("=" * 70)
    print("Historical Data Backfill - Ensure 1 Year Coverage")
    print("=" * 70)
    print()
    print("This script will:")
    print("  1. Check current historical data coverage for each stock")
    print("  2. Backfill missing data to reach 1 year (365 days)")
    print("  3. Show progress and statistics")
    print()

    target_days = 365

    # Process HKEX 18A companies
    print("=" * 70)
    print("HKEX 18A Biotech Companies")
    print("=" * 70)
    print()

    try:
        companies = get_hkex_biotech_companies()
        print(f"Found {len(companies)} HKEX 18A companies")
        print()

        total_backfilled = 0

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

            backfilled = check_and_backfill(ticker, ts_code, target_days)
            total_backfilled += backfilled
            print()

        print(f"HKEX 18A Summary: Backfilled {total_backfilled} total records")
        print()

    except Exception as e:
        logger.error(f"Error processing HKEX companies: {str(e)}")
        print(f"Error: {str(e)}")
        print()

    # Process Portfolio companies
    print("=" * 70)
    print("Portfolio Companies")
    print("=" * 70)
    print()

    try:
        print(f"Found {len(PORTFOLIO_COMPANIES)} portfolio companies")
        print()

        total_backfilled = 0

        for i, company in enumerate(PORTFOLIO_COMPANIES, 1):
            ticker = company['ticker']
            ts_code = company['ts_code']
            name = company['name']

            print(f"[{i}/{len(PORTFOLIO_COMPANIES)}] {ticker} - {name}")

            backfilled = check_and_backfill(ticker, ts_code, target_days)
            total_backfilled += backfilled
            print()

        print(f"Portfolio Summary: Backfilled {total_backfilled} total records")
        print()

    except Exception as e:
        logger.error(f"Error processing Portfolio companies: {str(e)}")
        print(f"Error: {str(e)}")
        print()

    # Final summary
    print("=" * 70)
    print("Backfill Complete")
    print("=" * 70)
    print()
    print("All stocks now have maximum available historical data.")
    print()
    print("Note: Some stocks may have less than 1 year of data if they:")
    print("  - Recently IPO'd (less than 1 year since listing)")
    print("  - Have limited data availability from API providers")
    print()


if __name__ == "__main__":
    main()
