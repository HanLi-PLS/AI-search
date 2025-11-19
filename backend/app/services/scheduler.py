"""
Scheduled tasks for automatic data refresh
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import logging
import requests

logger = logging.getLogger(__name__)

class DataRefreshScheduler:
    """Background scheduler for automatic data refresh"""

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.base_url = "http://localhost:8000"

    def start(self):
        """Start the scheduler with jobs for 12 AM and 12 PM"""
        # Refresh at 12 AM (midnight) every day
        self.scheduler.add_job(
            func=self.refresh_all_stock_data,
            trigger=CronTrigger(hour=0, minute=0),
            id='refresh_midnight',
            name='Refresh stock data at midnight',
            replace_existing=True
        )

        # Refresh at 12 PM (noon) every day
        self.scheduler.add_job(
            func=self.refresh_all_stock_data,
            trigger=CronTrigger(hour=12, minute=0),
            id='refresh_noon',
            name='Refresh stock data at noon',
            replace_existing=True
        )

        # Archive data older than 1 year to S3 weekly (Sunday at 2 AM)
        # This keeps SQLite lean while preserving historical data in S3
        self.scheduler.add_job(
            func=self.archive_old_data_to_s3,
            trigger=CronTrigger(day_of_week='sun', hour=2, minute=0),
            id='archive_weekly',
            name='Archive data older than 1 year to S3 weekly',
            replace_existing=True
        )

        self.scheduler.start()
        logger.info("Data refresh scheduler started (12 AM and 12 PM daily, archival of >1 year data on Sundays)")

    def stop(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()
        logger.info("Data refresh scheduler stopped")

    def refresh_all_stock_data(self):
        """Refresh all stock data (HKEX 18A + Portfolio) including historical data"""
        try:
            logger.info("Starting scheduled data refresh...")

            # Refresh HKEX 18A companies current prices
            try:
                response = requests.get(
                    f"{self.base_url}/api/stocks/prices?force_refresh=true",
                    timeout=300  # 5 minutes timeout
                )
                if response.status_code == 200:
                    logger.info("✓ HKEX 18A companies prices refreshed successfully")
                else:
                    logger.error(f"✗ HKEX 18A refresh failed: {response.status_code}")
            except Exception as e:
                logger.error(f"✗ Error refreshing HKEX 18A: {str(e)}")

            # Refresh Portfolio companies current prices
            try:
                response = requests.get(
                    f"{self.base_url}/api/stocks/portfolio?force_refresh=true",
                    timeout=60
                )
                if response.status_code == 200:
                    logger.info("✓ Portfolio companies prices refreshed successfully")
                else:
                    logger.error(f"✗ Portfolio refresh failed: {response.status_code}")
            except Exception as e:
                logger.error(f"✗ Error refreshing Portfolio: {str(e)}")

            # Update historical data for HKEX 18A companies
            try:
                response = requests.post(
                    f"{self.base_url}/api/stocks/bulk-update-history",
                    timeout=600  # 10 minutes timeout
                )
                if response.status_code == 200:
                    logger.info("✓ HKEX 18A historical data updated successfully")
                else:
                    logger.error(f"✗ HKEX 18A historical update failed: {response.status_code}")
            except Exception as e:
                logger.error(f"✗ Error updating HKEX 18A historical data: {str(e)}")

            # Update historical data for Portfolio companies
            try:
                from backend.app.services.portfolio import PORTFOLIO_COMPANIES
                for company in PORTFOLIO_COMPANIES:
                    ticker = company['ticker']
                    try:
                        response = requests.post(
                            f"{self.base_url}/api/stocks/{ticker}/update-history",
                            timeout=120  # 2 minutes per stock
                        )
                        if response.status_code == 200:
                            logger.info(f"✓ {ticker} historical data updated")
                        else:
                            logger.error(f"✗ {ticker} historical update failed: {response.status_code}")
                    except Exception as e:
                        logger.error(f"✗ Error updating {ticker} historical data: {str(e)}")
            except Exception as e:
                logger.error(f"✗ Error updating Portfolio historical data: {str(e)}")

            logger.info(f"Scheduled data refresh completed at {datetime.now()}")

        except Exception as e:
            logger.error(f"Error in scheduled data refresh: {str(e)}")

    def archive_old_data_to_s3(self):
        """Archive data older than 1 year from SQLite to S3"""
        try:
            logger.info("Starting scheduled data archival to S3 (>1 year old data)...")

            from backend.app.services.s3_storage import S3StockDataService
            from backend.app.api.routes.stocks import get_hkex_biotech_companies
            from backend.app.services.portfolio import PORTFOLIO_COMPANIES

            s3_service = S3StockDataService()

            # Archive HKEX 18A companies
            try:
                companies = get_hkex_biotech_companies()
                hkex_archived = 0
                hkex_deleted = 0

                for company in companies:
                    ticker = company['ticker']
                    archived, deleted = s3_service.archive_old_data(ticker, older_than_days=365)
                    hkex_archived += archived
                    hkex_deleted += deleted

                logger.info(f"✓ HKEX 18A: Archived {hkex_archived} records, deleted {hkex_deleted} from SQLite")
            except Exception as e:
                logger.error(f"✗ Error archiving HKEX data: {str(e)}")

            # Archive Portfolio companies
            try:
                portfolio_archived = 0
                portfolio_deleted = 0

                for company in PORTFOLIO_COMPANIES:
                    ticker = company['ticker']
                    archived, deleted = s3_service.archive_old_data(ticker, older_than_days=365)
                    portfolio_archived += archived
                    portfolio_deleted += deleted

                logger.info(f"✓ Portfolio: Archived {portfolio_archived} records, deleted {portfolio_deleted} from SQLite")
            except Exception as e:
                logger.error(f"✗ Error archiving Portfolio data: {str(e)}")

            logger.info(f"Scheduled data archival completed at {datetime.now()}")

        except Exception as e:
            logger.error(f"Error in scheduled data archival: {str(e)}")


# Global scheduler instance
_scheduler = None

def get_scheduler() -> DataRefreshScheduler:
    """Get or create the global scheduler instance"""
    global _scheduler
    if _scheduler is None:
        _scheduler = DataRefreshScheduler()
    return _scheduler
