#!/usr/bin/env python3
"""
Verify and fix database status
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from backend.app.database import get_session_local
from backend.app.models.stock import StockDaily
from sqlalchemy import func
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Check database status and record counts"""
    print("=" * 70)
    print("Database Status Check")
    print("=" * 70)
    print()

    session_local = get_session_local()
    db = session_local()

    try:
        # Total records
        total = db.query(func.count(StockDaily.id)).scalar()
        print(f"Total records in database: {total}")
        print()

        if total == 0:
            print("⚠️  Database is empty!")
            print()
            print("This means historical data needs to be fetched.")
            print("Run: python3 backfill_full_year.py")
            print()
        else:
            # Get per-ticker stats
            print("Records per ticker:")
            print("-" * 70)

            results = db.query(
                StockDaily.ticker,
                func.count(StockDaily.id).label('count'),
                func.min(StockDaily.trade_date).label('earliest'),
                func.max(StockDaily.trade_date).label('latest')
            ).group_by(StockDaily.ticker).order_by(func.count(StockDaily.id).desc()).limit(10).all()

            for ticker, count, earliest, latest in results:
                days = (latest - earliest).days if earliest and latest else 0
                print(f"{ticker:12} {count:6} records   {earliest} to {latest}  ({days} days)")

            print()
            print(f"Total unique stocks: {db.query(func.count(func.distinct(StockDaily.ticker))).scalar()}")

    finally:
        db.close()

if __name__ == "__main__":
    main()
