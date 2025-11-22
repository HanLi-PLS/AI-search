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

    def _fetch_us_stock_from_finnhub(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        db: Session
    ) -> int:
        """
        Fetch US stock historical data from Finnhub

        Args:
            ticker: Stock ticker (e.g., "ZBIO")
            start_date: Start date in YYYYMMDD format
            end_date: End date in YYYYMMDD format
            db: Database session

        Returns:
            Number of records stored
        """
        try:
            import finnhub
            from backend.app.config import settings

            if not settings.FINNHUB_API_KEY:
                logger.error(f"Finnhub API key not available for {ticker} - cannot fetch US stock data")
                logger.error("Check AWS Secrets Manager for 'finnhub-api-key' or set FINNHUB_API_KEY in .env")
                return 0

            logger.info(f"Using Finnhub API key: {settings.FINNHUB_API_KEY[:10]}... for {ticker}")
            finnhub_client = finnhub.Client(api_key=settings.FINNHUB_API_KEY)

            # Convert date format from YYYYMMDD to Unix timestamp
            start_dt = datetime.strptime(start_date, '%Y%m%d')
            end_dt = datetime.strptime(end_date, '%Y%m%d')

            start_timestamp = int(start_dt.timestamp())
            # Add 1 day to end_timestamp to include the end date (Finnhub uses timestamp at midnight,
            # so to include Nov 18's data, we need timestamp of Nov 19 00:00:00)
            end_dt_inclusive = end_dt + timedelta(days=1)
            end_timestamp = int(end_dt_inclusive.timestamp())

            # Fetch candle data (daily OHLCV)
            logger.info(f"Fetching Finnhub candles for {ticker} from {start_date} to {end_date}")
            res = finnhub_client.stock_candles(ticker, 'D', start_timestamp, end_timestamp)

            if res.get('s') != 'ok' or not res.get('c'):
                logger.warning(f"Finnhub candles not available for {ticker}: status={res.get('s')}")
                logger.info(f"Falling back to yfinance for {ticker} historical data")
                return self._fetch_us_stock_from_yfinance(ticker, start_date, end_date, db)

            records_stored = 0

            # Process each candle
            for i in range(len(res['c'])):
                trade_date = datetime.fromtimestamp(res['t'][i]).date()

                # Check if record already exists
                existing = db.query(StockDaily).filter(
                    and_(
                        StockDaily.ticker == ticker,
                        StockDaily.trade_date == trade_date
                    )
                ).first()

                close_price = float(res['c'][i])
                open_price = float(res['o'][i])
                high_price = float(res['h'][i])
                low_price = float(res['l'][i])
                volume = float(res['v'][i])

                if existing:
                    # Update existing record
                    existing.open = open_price
                    existing.high = high_price
                    existing.low = low_price
                    existing.close = close_price
                    existing.volume = volume
                    existing.updated_at = datetime.now()
                else:
                    # Create new record
                    stock_daily = StockDaily(
                        ticker=ticker,
                        ts_code=ticker,
                        trade_date=trade_date,
                        open=open_price,
                        high=high_price,
                        low=low_price,
                        close=close_price,
                        volume=volume,
                        data_source="Finnhub"
                    )
                    db.add(stock_daily)

                records_stored += 1

            db.commit()
            logger.info(f"Stored {records_stored} Finnhub records for {ticker}")
            return records_stored

        except Exception as e:
            logger.warning(f"Finnhub failed for {ticker}: {str(e)}")
            logger.info(f"Falling back to yfinance for {ticker} historical data")
            return self._fetch_us_stock_from_yfinance(ticker, start_date, end_date, db)

    def _fetch_us_stock_from_yfinance(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        db: Session
    ) -> int:
        """
        Fetch US stock historical data from yfinance (fallback when Finnhub fails)

        Args:
            ticker: Stock ticker (e.g., "ZBIO")
            start_date: Start date in YYYYMMDD format
            end_date: End date in YYYYMMDD format
            db: Database session

        Returns:
            Number of records stored
        """
        try:
            import yfinance as yf

            # Convert date format from YYYYMMDD to YYYY-MM-DD
            start_dt = datetime.strptime(start_date, '%Y%m%d')
            end_dt = datetime.strptime(end_date, '%Y%m%d')

            # yfinance's end parameter is EXCLUSIVE, so add 1 day to include the end date
            end_dt_inclusive = end_dt + timedelta(days=1)

            start_str = start_dt.strftime('%Y-%m-%d')
            end_str = end_dt_inclusive.strftime('%Y-%m-%d')

            logger.info(f"Fetching yfinance data for {ticker} from {start_str} to {end_str}")

            # Fetch historical data
            stock = yf.Ticker(ticker)
            df = stock.history(start=start_str, end=end_str)

            if df is None or df.empty:
                logger.warning(f"No yfinance data for {ticker}")
                return 0

            records_stored = 0

            # Process each row
            for trade_date, row in df.iterrows():
                trade_date = trade_date.date()

                # Check if record already exists
                existing = db.query(StockDaily).filter(
                    and_(
                        StockDaily.ticker == ticker,
                        StockDaily.trade_date == trade_date
                    )
                ).first()

                close_price = float(row['Close'])
                open_price = float(row['Open'])
                high_price = float(row['High'])
                low_price = float(row['Low'])
                volume = float(row['Volume'])

                if existing:
                    # Update existing record
                    existing.open = open_price
                    existing.high = high_price
                    existing.low = low_price
                    existing.close = close_price
                    existing.volume = volume
                    existing.updated_at = datetime.now()
                else:
                    # Create new record
                    stock_daily = StockDaily(
                        ticker=ticker,
                        ts_code=ticker,
                        trade_date=trade_date,
                        open=open_price,
                        high=high_price,
                        low=low_price,
                        close=close_price,
                        volume=volume,
                        data_source="Yahoo Finance"
                    )
                    db.add(stock_daily)

                records_stored += 1

            db.commit()
            logger.info(f"Stored {records_stored} yfinance records for {ticker}")
            return records_stored

        except Exception as e:
            logger.error(f"Error fetching yfinance data for {ticker}: {str(e)}")
            db.rollback()
            return 0

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

            # Determine if this is a US stock or HK stock based on ts_code
            # HK stocks end with .HK (e.g., 02561.HK)
            # US stocks don't have suffix (e.g., ZBIO, AAPL)
            is_us_stock = not ts_code.endswith('.HK')

            # Fetch data from appropriate source
            if is_us_stock:
                # Use yfinance as primary for US stocks (more reliable for smaller NASDAQ stocks like ZBIO)
                logger.info(f"Fetching US stock data from yfinance for {ticker} ({ts_code})")
                return self._fetch_us_stock_from_yfinance(ticker, start_date, end_date, db)
            else:
                logger.info(f"Fetching HK stock data for {ticker} ({ts_code})")
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
                # No data exists, fetch last 365 days (1 year)
                start_date = (date.today() - timedelta(days=365)).strftime('%Y%m%d')

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

    def backfill_historical_data(self, ticker: str, ts_code: str, days: int = 365, db: Session = None) -> int:
        """
        Backfill older historical data for a stock that already has some data.
        Fetches data from (earliest_date - days) to earliest_date.

        Args:
            ticker: Stock ticker (e.g., "1801.HK")
            ts_code: Tushare format code (e.g., "01801.HK")
            days: Number of days to backfill (default: 365)
            db: Database session (optional)

        Returns:
            Number of new records stored
        """
        close_db = False
        if db is None:
            db = self.get_db()
            close_db = True

        try:
            # Get earliest date we have
            earliest_date = db.query(func.min(StockDaily.trade_date)).filter(
                StockDaily.ticker == ticker
            ).scalar()

            if not earliest_date:
                # No data exists, use regular update_incremental instead
                logger.info(f"No existing data for {ticker}, use update_incremental instead")
                return 0

            # Calculate backfill range
            end_date = (earliest_date - timedelta(days=1)).strftime('%Y%m%d')
            start_date = (earliest_date - timedelta(days=days)).strftime('%Y%m%d')

            logger.info(f"Backfilling {ticker} from {start_date} to {end_date}")

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
        Retrieve historical data from database (SQLite) and S3 (if needed)

        Hybrid approach:
        - Recent data (last 90 days): Fetched from SQLite (fast)
        - Older data: Fetched from S3 (archived)

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
            # Query SQLite first
            query = db.query(StockDaily).filter(StockDaily.ticker == ticker)

            if start_date:
                query = query.filter(StockDaily.trade_date >= start_date)
            if end_date:
                query = query.filter(StockDaily.trade_date <= end_date)

            query = query.order_by(desc(StockDaily.trade_date))

            if limit:
                query = query.limit(limit)

            records = query.all()
            sqlite_data = [record.to_dict() for record in records]

            # Check if we need to fetch from S3 for older data
            # If start_date is requested and we don't have data going back that far
            if start_date and sqlite_data:
                # Find earliest date in SQLite results
                earliest_sqlite = min(
                    datetime.fromisoformat(r['trade_date']).date()
                    for r in sqlite_data
                )

                # If there's a gap, fetch from S3
                if earliest_sqlite > start_date:
                    logger.info(f"Fetching older data for {ticker} from S3 ({start_date} to {earliest_sqlite})")
                    try:
                        from backend.app.services.s3_storage import S3StockDataService
                        s3_service = S3StockDataService()

                        # Fetch missing data from S3
                        s3_data = s3_service.load_from_s3(
                            ticker=ticker,
                            start_date=start_date,
                            end_date=earliest_sqlite - timedelta(days=1)
                        )

                        if s3_data:
                            logger.info(f"Loaded {len(s3_data)} records from S3 for {ticker}")
                            # Combine SQLite and S3 data
                            all_data = sqlite_data + s3_data
                            # Sort by date descending
                            all_data.sort(
                                key=lambda x: datetime.fromisoformat(x['trade_date']),
                                reverse=True
                            )
                            return all_data
                    except Exception as e:
                        logger.warning(f"Failed to fetch from S3 for {ticker}: {str(e)}")
                        # Continue with SQLite data only

            return sqlite_data

        finally:
            if close_db:
                db.close()

    def fetch_and_store_capiq_history(
        self,
        ticker: str,
        days: int = 90,
        db: Session = None
    ) -> int:
        """
        Fetch historical price data from CapIQ and store in database

        Args:
            ticker: Stock ticker (e.g., "2561.HK")
            days: Number of days of history to fetch (default 90)
            db: Database session (optional)

        Returns:
            Number of records stored/updated
        """
        from backend.app.services.capiq_data import get_capiq_service

        close_db = False
        if db is None:
            db = self.get_db()
            close_db = True

        try:
            # Determine market based on ticker
            market = "HK" if ".HK" in ticker.upper() else "US"

            # Fetch historical data from CapIQ
            capiq_service = get_capiq_service()
            if not capiq_service.available:
                logger.warning(f"CapIQ not available for {ticker}")
                return 0

            historical_data = capiq_service.get_historical_prices(
                ticker=ticker,
                market=market,
                days=days
            )

            if not historical_data:
                logger.warning(f"No CapIQ historical data found for {ticker}")
                return 0

            records_stored = 0

            for record in historical_data:
                trade_date = record['trade_date']
                if isinstance(trade_date, str):
                    trade_date = datetime.fromisoformat(trade_date).date()

                # Check if record already exists
                existing = db.query(StockDaily).filter(
                    and_(
                        StockDaily.ticker == ticker,
                        StockDaily.trade_date == trade_date
                    )
                ).first()

                close_price = record.get('close')
                open_price = record.get('open')
                high_price = record.get('high')
                low_price = record.get('low')
                volume = record.get('volume')

                if existing:
                    # Update existing record with CapIQ data
                    existing.open = open_price
                    existing.high = high_price
                    existing.low = low_price
                    existing.close = close_price
                    existing.volume = volume
                    existing.data_source = "CapIQ"
                    existing.updated_at = datetime.now()
                else:
                    # Create new record
                    stock_daily = StockDaily(
                        ticker=ticker,
                        ts_code=ticker,  # Use ticker as ts_code for CapIQ data
                        trade_date=trade_date,
                        open=open_price,
                        high=high_price,
                        low=low_price,
                        close=close_price,
                        volume=volume,
                        data_source="CapIQ"
                    )
                    db.add(stock_daily)

                records_stored += 1

            db.commit()
            logger.info(f"Stored {records_stored} CapIQ historical records for {ticker}")
            return records_stored

        except Exception as e:
            logger.error(f"Failed to fetch/store CapIQ history for {ticker}: {str(e)}")
            db.rollback()
            return 0
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

    def bulk_backfill_all_stocks(self, tickers: List[tuple], days: int = 365, db: Session = None) -> Dict[str, int]:
        """
        Backfill older historical data for all stocks

        Args:
            tickers: List of (ticker, ts_code) tuples
            days: Number of days to backfill for each stock (default: 365)
            db: Database session (optional)

        Returns:
            Dictionary with backfill statistics
        """
        close_db = False
        if db is None:
            db = self.get_db()
            close_db = True

        stats = {
            'total': len(tickers),
            'backfilled': 0,
            'new_records': 0,
            'errors': 0,
            'skipped': 0  # Stocks with no existing data
        }

        try:
            for ticker, ts_code in tickers:
                try:
                    new_records = self.backfill_historical_data(ticker, ts_code, days, db)
                    if new_records > 0:
                        stats['backfilled'] += 1
                        stats['new_records'] += new_records
                    elif new_records == 0:
                        # Check if it was skipped (no existing data)
                        existing_count = db.query(func.count(StockDaily.id)).filter(
                            StockDaily.ticker == ticker
                        ).scalar()
                        if existing_count == 0:
                            stats['skipped'] += 1
                except Exception as e:
                    logger.error(f"Error backfilling {ticker}: {str(e)}")
                    stats['errors'] += 1

            return stats
        finally:
            if close_db:
                db.close()
