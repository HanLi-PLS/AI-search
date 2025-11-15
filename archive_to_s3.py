#!/usr/bin/env python3
"""
Manual script to archive old historical data from SQLite to S3
Archives data older than 1 year (365 days) to reduce local storage usage
"""
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.app.services.s3_storage import S3StockDataService
from backend.app.api.routes.stocks import get_hkex_biotech_companies
from backend.app.services.portfolio import PORTFOLIO_COMPANIES
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Archive old data to S3"""
    print("=" * 60)
    print("Archive Historical Data to S3")
    print("=" * 60)
    print()
    print("This script will:")
    print("  1. Archive data older than 1 year (365 days) from SQLite to S3")
    print("  2. Delete archived data from SQLite to free up space")
    print("  3. Store data in parquet format (compressed)")
    print()
    print("S3 Locations:")
    print("  - HKEX 18A: s3://plfs-han-ai-search/public_company_tracker/hkex_18a_stocks/")
    print("  - Portfolio: s3://plfs-han-ai-search/public_company_tracker/portfolio_comps_tracker/")
    print()

    # Confirm
    response = input("Continue? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Aborted.")
        return

    print()
    logger.info("Starting data archival process...")

    s3_service = S3StockDataService()

    # Archive HKEX 18A companies
    print("\n" + "=" * 60)
    print("Archiving HKEX 18A Companies")
    print("=" * 60)

    try:
        companies = get_hkex_biotech_companies()
        logger.info(f"Found {len(companies)} HKEX 18A companies")

        total_archived = 0
        total_deleted = 0

        for i, company in enumerate(companies, 1):
            ticker = company['ticker']
            name = company['name']

            print(f"\n[{i}/{len(companies)}] Processing {ticker} ({name})...")

            try:
                archived, deleted = s3_service.archive_old_data(ticker, older_than_days=365)

                if archived > 0:
                    print(f"  ✓ Archived {archived} records, deleted {deleted} from SQLite")
                    total_archived += archived
                    total_deleted += deleted
                else:
                    print(f"  - No old data to archive")

            except Exception as e:
                print(f"  ✗ Error: {str(e)}")
                logger.error(f"Error archiving {ticker}: {str(e)}")

        print()
        logger.info(f"HKEX 18A Summary: Archived {total_archived} records, deleted {total_deleted} from SQLite")

    except Exception as e:
        logger.error(f"Error processing HKEX companies: {str(e)}")

    # Archive Portfolio companies
    print("\n" + "=" * 60)
    print("Archiving Portfolio Companies")
    print("=" * 60)

    try:
        logger.info(f"Found {len(PORTFOLIO_COMPANIES)} portfolio companies")

        total_archived = 0
        total_deleted = 0

        for i, company in enumerate(PORTFOLIO_COMPANIES, 1):
            ticker = company['ticker']
            name = company['name']

            print(f"\n[{i}/{len(PORTFOLIO_COMPANIES)}] Processing {ticker} ({name})...")

            try:
                archived, deleted = s3_service.archive_old_data(ticker, older_than_days=365)

                if archived > 0:
                    print(f"  ✓ Archived {archived} records, deleted {deleted} from SQLite")
                    total_archived += archived
                    total_deleted += deleted
                else:
                    print(f"  - No old data to archive")

            except Exception as e:
                print(f"  ✗ Error: {str(e)}")
                logger.error(f"Error archiving {ticker}: {str(e)}")

        print()
        logger.info(f"Portfolio Summary: Archived {total_archived} records, deleted {total_deleted} from SQLite")

    except Exception as e:
        logger.error(f"Error processing Portfolio companies: {str(e)}")

    # Final summary
    print("\n" + "=" * 60)
    print("Archival Complete")
    print("=" * 60)
    print()
    print("Notes:")
    print("  - Archived data is stored in S3 in parquet format")
    print("  - Data is partitioned by year/month for efficient queries")
    print("  - Charts will automatically fetch from S3 if needed")
    print("  - Weekly archival runs automatically (Sunday 2 AM)")
    print()


if __name__ == "__main__":
    main()
