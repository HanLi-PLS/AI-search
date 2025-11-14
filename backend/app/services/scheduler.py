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

        self.scheduler.start()
        logger.info("Data refresh scheduler started (12 AM and 12 PM)")

    def stop(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()
        logger.info("Data refresh scheduler stopped")

    def refresh_all_stock_data(self):
        """Refresh all stock data (HKEX 18A + Portfolio)"""
        try:
            logger.info("Starting scheduled data refresh...")

            # Refresh HKEX 18A companies
            try:
                response = requests.get(
                    f"{self.base_url}/api/stocks/prices?force_refresh=true",
                    timeout=300  # 5 minutes timeout
                )
                if response.status_code == 200:
                    logger.info("✓ HKEX 18A companies refreshed successfully")
                else:
                    logger.error(f"✗ HKEX 18A refresh failed: {response.status_code}")
            except Exception as e:
                logger.error(f"✗ Error refreshing HKEX 18A: {str(e)}")

            # Refresh Portfolio companies
            try:
                response = requests.get(
                    f"{self.base_url}/api/stocks/portfolio?force_refresh=true",
                    timeout=60
                )
                if response.status_code == 200:
                    logger.info("✓ Portfolio companies refreshed successfully")
                else:
                    logger.error(f"✗ Portfolio refresh failed: {response.status_code}")
            except Exception as e:
                logger.error(f"✗ Error refreshing Portfolio: {str(e)}")

            logger.info(f"Scheduled data refresh completed at {datetime.now()}")

        except Exception as e:
            logger.error(f"Error in scheduled data refresh: {str(e)}")


# Global scheduler instance
_scheduler = None

def get_scheduler() -> DataRefreshScheduler:
    """Get or create the global scheduler instance"""
    global _scheduler
    if _scheduler is None:
        _scheduler = DataRefreshScheduler()
    return _scheduler
