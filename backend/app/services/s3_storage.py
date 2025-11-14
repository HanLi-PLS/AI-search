"""
S3 Storage Service for Historical Stock Data
Provides efficient storage and retrieval of historical stock data using S3
"""
import logging
import pandas as pd
import boto3
from io import BytesIO
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from backend.app.config import settings

logger = logging.getLogger(__name__)


class S3StockDataService:
    """Service for managing historical stock data in S3"""

    def __init__(self):
        """Initialize S3 client"""
        self.s3_client = boto3.client(
            's3',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        self.bucket = "plfs-han-ai-search"
        self.hkex_prefix = "public_company_tracker/hkex_18a_stocks/"
        self.portfolio_prefix = "public_company_tracker/portfolio_comps_tracker/"

    def _get_s3_key(self, ticker: str, year: int, month: int) -> tuple[str, str]:
        """
        Generate S3 key for a ticker's data

        Args:
            ticker: Stock ticker (e.g., "2561.HK", "ZBIO")
            year: Year
            month: Month

        Returns:
            Tuple of (prefix, full_key)
        """
        # Determine if it's HKEX or portfolio company
        is_hkex = ticker.endswith('.HK')
        prefix = self.hkex_prefix if is_hkex else self.portfolio_prefix

        # Format: hkex_18a_stocks/2561.HK/2024/01.parquet
        key = f"{prefix}{ticker}/{year}/{month:02d}.parquet"
        return prefix, key

    def save_to_s3(self, ticker: str, data: List[Dict[str, Any]]) -> bool:
        """
        Save historical data to S3 in parquet format, partitioned by year/month

        Args:
            ticker: Stock ticker
            data: List of daily records

        Returns:
            True if successful
        """
        try:
            if not data:
                logger.warning(f"No data to save for {ticker}")
                return False

            # Convert to DataFrame
            df = pd.DataFrame(data)

            # Convert trade_date to datetime if it's string
            if 'trade_date' in df.columns:
                df['trade_date'] = pd.to_datetime(df['trade_date'])

            # Group by year and month
            df['year'] = df['trade_date'].dt.year
            df['month'] = df['trade_date'].dt.month

            # Save each year/month partition separately
            saved_count = 0
            for (year, month), group_df in df.groupby(['year', 'month']):
                # Remove year/month columns before saving
                group_df = group_df.drop(columns=['year', 'month'])

                # Generate S3 key
                prefix, s3_key = self._get_s3_key(ticker, year, month)

                # Convert to parquet
                parquet_buffer = BytesIO()
                group_df.to_parquet(parquet_buffer, engine='pyarrow', compression='snappy', index=False)
                parquet_buffer.seek(0)

                # Upload to S3
                self.s3_client.put_object(
                    Bucket=self.bucket,
                    Key=s3_key,
                    Body=parquet_buffer.getvalue(),
                    ContentType='application/x-parquet'
                )

                saved_count += len(group_df)
                logger.info(f"Saved {len(group_df)} records for {ticker} {year}-{month:02d} to S3: {s3_key}")

            logger.info(f"Successfully saved {saved_count} total records for {ticker} to S3")
            return True

        except Exception as e:
            logger.error(f"Error saving {ticker} to S3: {str(e)}")
            return False

    def load_from_s3(
        self,
        ticker: str,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """
        Load historical data from S3 for a date range

        Args:
            ticker: Stock ticker
            start_date: Start date
            end_date: End date

        Returns:
            List of daily records
        """
        try:
            all_data = []

            # Generate list of year/month combinations to fetch
            current = start_date.replace(day=1)
            end = end_date.replace(day=1)

            while current <= end:
                year = current.year
                month = current.month

                prefix, s3_key = self._get_s3_key(ticker, year, month)

                try:
                    # Fetch from S3
                    response = self.s3_client.get_object(
                        Bucket=self.bucket,
                        Key=s3_key
                    )

                    # Read parquet data
                    parquet_data = response['Body'].read()
                    df = pd.read_parquet(BytesIO(parquet_data))

                    # Convert to dict
                    records = df.to_dict('records')

                    # Filter by date range
                    for record in records:
                        trade_date = pd.to_datetime(record['trade_date']).date()
                        if start_date <= trade_date <= end_date:
                            # Convert trade_date to string for JSON serialization
                            record['trade_date'] = trade_date.isoformat()
                            all_data.append(record)

                    logger.info(f"Loaded {len(records)} records for {ticker} {year}-{month:02d} from S3")

                except self.s3_client.exceptions.NoSuchKey:
                    logger.debug(f"No S3 data found for {ticker} {year}-{month:02d}")
                except Exception as e:
                    logger.warning(f"Error loading {ticker} {year}-{month:02d} from S3: {str(e)}")

                # Move to next month
                if month == 12:
                    current = current.replace(year=year + 1, month=1)
                else:
                    current = current.replace(month=month + 1)

            logger.info(f"Loaded {len(all_data)} total records for {ticker} from S3")
            return all_data

        except Exception as e:
            logger.error(f"Error loading {ticker} from S3: {str(e)}")
            return []

    def archive_old_data(self, ticker: str, older_than_days: int = 365) -> tuple[int, int]:
        """
        Archive data older than specified days from SQLite to S3

        Args:
            ticker: Stock ticker
            older_than_days: Archive data older than this many days (default: 365)

        Returns:
            Tuple of (records_archived, records_deleted)
        """
        try:
            from backend.app.services.stock_data import StockDataService
            from backend.app.models.stock import StockDaily
            from backend.app.database import get_session_local

            # Get database session
            session_local = get_session_local()
            db = session_local()

            try:
                # Get cutoff date
                cutoff_date = date.today() - timedelta(days=older_than_days)

                # Query old records
                old_records = db.query(StockDaily).filter(
                    StockDaily.ticker == ticker,
                    StockDaily.trade_date < cutoff_date
                ).all()

                if not old_records:
                    logger.info(f"No old data to archive for {ticker}")
                    return 0, 0

                # Convert to dict list
                data_to_archive = [record.to_dict() for record in old_records]

                # Save to S3
                if self.save_to_s3(ticker, data_to_archive):
                    # Delete from SQLite
                    deleted_count = db.query(StockDaily).filter(
                        StockDaily.ticker == ticker,
                        StockDaily.trade_date < cutoff_date
                    ).delete()

                    db.commit()

                    logger.info(f"Archived and deleted {deleted_count} old records for {ticker}")
                    return len(data_to_archive), deleted_count
                else:
                    logger.error(f"Failed to save {ticker} to S3, keeping data in SQLite")
                    return 0, 0

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error archiving {ticker}: {str(e)}")
            return 0, 0

    def list_archived_tickers(self, is_hkex: bool = True) -> List[str]:
        """
        List all tickers that have archived data in S3

        Args:
            is_hkex: True for HKEX stocks, False for portfolio companies

        Returns:
            List of ticker symbols
        """
        try:
            prefix = self.hkex_prefix if is_hkex else self.portfolio_prefix

            # List objects with prefix
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix,
                Delimiter='/'
            )

            # Extract ticker names from CommonPrefixes
            tickers = []
            if 'CommonPrefixes' in response:
                for common_prefix in response['CommonPrefixes']:
                    # Extract ticker from path like "hkex_18a_stocks/2561.HK/"
                    ticker = common_prefix['Prefix'].replace(prefix, '').rstrip('/')
                    if ticker:
                        tickers.append(ticker)

            return tickers

        except Exception as e:
            logger.error(f"Error listing archived tickers: {str(e)}")
            return []
