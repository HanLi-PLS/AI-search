"""
Service layer for managing historical stock data
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
import logging
import tushare as ts
from backend.app.models.stock import StockDaily
from backend.app.database import get_session_local
from backend.app.config import settings

logger = logging.getLogger(__name__)


class StockDataService:
    """Service for managing historical stock data in database"""

    def __init__(self):
        self.tushare_token = settings.TUSHARE_API_TOKEN
        if self.tushare_token:
            ts.set_token(self.tushare_token)

    def get_db(self) -> Session:
        """Get database session"""
        session_local = get_session_local()
        return session_local()

    def get_latest_date(self, ticker: str, db: Session = None) -> Optional[date]:
        """
        Get the latest date we have data for a specific ticker

        Args:
            ticker: Stock ticker (e.g., "1801.HK")
            db: Database session (optional)

        Returns:
            Latest date or None if no data exists
        """
        close_db = False
        if db is None:
            db = self.get_db()
            close_db = True

        try:
            result = db.query(func.max(StockDaily.trade_date)).filter(
                StockDaily.ticker == ticker
            ).scalar()
            return result
        finally:
            if close_db:
                db.close()

    def fetch_and_store_historical_data(
        self,
        ticker: str,
        ts_code: str,
        start_date: str = None,
        end_date: str = None,
        db: Session = None
    ) -> int:
        """
        Fetch historical data from Tushare and store in database

        Args:
            ticker: Stock ticker (e.g., "1801.HK")
            ts_code: Tushare format code (e.g., "01801.HK")
            start_date: Start date in YYYYMMDD format (optional)
            end_date: End date in YYYYMMDD format (optional)
            db: Database session (optional)

        Returns:
            Number of records stored
        """
        if not self.tushare_token:
            logger.warning("Tushare token not available, cannot fetch historical data")
            return 0

        close_db = False
        if db is None:
            db = self.get_db()
            close_db = True

        try:
            pro = ts.pro_api()

            # Fetch data from Tushare
            df = pro.hk_daily(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )

            if df is None or df.empty:
                logger.info(f"No historical data found for {ticker}")
                return 0

            records_stored = 0

            # Process each row and store in database
            for _, row in df.iterrows():
                trade_date = datetime.strptime(row['trade_date'], '%Y%m%d').date()

                # Check if record already exists
                existing = db.query(StockDaily).filter(
                    and_(
                        StockDaily.ticker == ticker,
                        StockDaily.trade_date == trade_date
                    )
                ).first()

                if existing:
                    # Update existing record
                    existing.open = float(row['open']) if row['open'] else None
                    existing.high = float(row['high']) if row['high'] else None
                    existing.low = float(row['low']) if row['low'] else None
                    existing.close = float(row['close'])
                    existing.pre_close = float(row['pre_close']) if row['pre_close'] else None
                    existing.volume = float(row['vol']) if row['vol'] else None
                    existing.amount = float(row['amount']) if row['amount'] else None
                    existing.change = float(row['change']) if 'change' in row and row['change'] else None
                    existing.pct_change = float(row['pct_chg']) if 'pct_chg' in row and row['pct_chg'] else None
                    existing.updated_at = datetime.now()
                else:
                    # Create new record
                    stock_daily = StockDaily(
                        ticker=ticker,
                        ts_code=ts_code,
                        trade_date=trade_date,
                        open=float(row['open']) if row['open'] else None,
                        high=float(row['high']) if row['high'] else None,
                        low=float(row['low']) if row['low'] else None,
                        close=float(row['close']),
                        pre_close=float(row['pre_close']) if row['pre_close'] else None,
                        volume=float(row['vol']) if row['vol'] else None,
                        amount=float(row['amount']) if row['amount'] else None,
                        change=float(row['change']) if 'change' in row and row['change'] else None,
                        pct_change=float(row['pct_chg']) if 'pct_chg' in row and row['pct_chg'] else None,
                        data_source="Tushare Pro"
                    )
                    db.add(stock_daily)

                records_stored += 1

            db.commit()
            logger.info(f"Stored {records_stored} records for {ticker}")
            return records_stored

        except Exception as e:
            logger.error(f"Error fetching/storing historical data for {ticker}: {str(e)}")
            db.rollback()
            return 0
        finally:
            if close_db:
                db.close()

    def update_incremental(self, ticker: str, ts_code: str, db: Session = None) -> int:
        """
        Fetch only new data since the last update

        Args:
            ticker: Stock ticker (e.g., "1801.HK")
            ts_code: Tushare format code (e.g., "01801.HK")
            db: Database session (optional)

        Returns:
            Number of new records stored
        """
        close_db = False
        if db is None:
            db = self.get_db()
            close_db = True

        try:
            # Get latest date we have
            latest_date = self.get_latest_date(ticker, db)

            if latest_date:
                # Fetch from day after latest date to today
                start_date = (latest_date + timedelta(days=1)).strftime('%Y%m%d')
            else:
                # No data exists, fetch last 90 days
                start_date = (date.today() - timedelta(days=90)).strftime('%Y%m%d')

            end_date = date.today().strftime('%Y%m%d')

            logger.info(f"Updating {ticker} from {start_date} to {end_date}")

            return self.fetch_and_store_historical_data(
                ticker=ticker,
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
                db=db
            )
        finally:
            if close_db:
                db.close()

    def get_historical_data(
        self,
        ticker: str,
        start_date: date = None,
        end_date: date = None,
        limit: int = None,
        db: Session = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve historical data from database

        Args:
            ticker: Stock ticker (e.g., "1801.HK")
            start_date: Start date (optional)
            end_date: End date (optional)
            limit: Maximum number of records to return (optional)
            db: Database session (optional)

        Returns:
            List of historical data dictionaries
        """
        close_db = False
        if db is None:
            db = self.get_db()
            close_db = True

        try:
            query = db.query(StockDaily).filter(StockDaily.ticker == ticker)

            if start_date:
                query = query.filter(StockDaily.trade_date >= start_date)
            if end_date:
                query = query.filter(StockDaily.trade_date <= end_date)

            query = query.order_by(desc(StockDaily.trade_date))

            if limit:
                query = query.limit(limit)

            records = query.all()
            return [record.to_dict() for record in records]

        finally:
            if close_db:
                db.close()

    def bulk_update_all_stocks(self, tickers: List[tuple], db: Session = None) -> Dict[str, int]:
        """
        Update all stocks incrementally

        Args:
            tickers: List of (ticker, ts_code) tuples
            db: Database session (optional)

        Returns:
            Dictionary with update statistics
        """
        close_db = False
        if db is None:
            db = self.get_db()
            close_db = True

        stats = {
            'total': len(tickers),
            'updated': 0,
            'new_records': 0,
            'errors': 0
        }

        try:
            for ticker, ts_code in tickers:
                try:
                    new_records = self.update_incremental(ticker, ts_code, db)
                    if new_records > 0:
                        stats['updated'] += 1
                        stats['new_records'] += new_records
                except Exception as e:
                    logger.error(f"Error updating {ticker}: {str(e)}")
                    stats['errors'] += 1

            return stats
        finally:
            if close_db:
                db.close()
