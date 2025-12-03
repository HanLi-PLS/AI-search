"""
IPO Data Service - Reads and processes IPO tracker data from S3
"""
import logging
import pandas as pd
import boto3
from io import BytesIO
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Global cache for IPO data (lasts 5 minutes)
_ipo_cache = {
    'data': None,
    'timestamp': None,
    's3_key': None
}


class IPODataService:
    """Service for reading and processing IPO tracker data from S3"""

    def __init__(self, bucket_name: str = "plfs-han-ai-search", region: str = "us-west-2"):
        """
        Initialize IPO data service

        Args:
            bucket_name: S3 bucket name
            region: AWS region
        """
        self.bucket_name = bucket_name
        self.region = region
        self.s3_client = boto3.client('s3', region_name=region)
        logger.info(f"IPO Data Service initialized with bucket: {bucket_name}")

    def read_html_from_s3(self, s3_key: str) -> str:
        """
        Read HTML file from S3 and return as string

        Args:
            s3_key: S3 object key (e.g., "public_company_tracker/hkex_ipo_tracker/hkex_ipo_report_20251116_222848.html")

        Returns:
            HTML content as string
        """
        try:
            logger.info(f"Reading HTML from s3://{self.bucket_name}/{s3_key}")

            # Download file from S3
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            html_content = response['Body'].read().decode('utf-8')

            logger.info(f"Successfully read HTML file ({len(html_content)} characters)")
            return html_content

        except Exception as e:
            logger.error(f"Error reading HTML from S3: {str(e)}")
            raise

    def read_ipo_tracker_from_s3(self, s3_key: str) -> pd.DataFrame:
        """
        Read CSV or Excel file from S3 and return as DataFrame

        Args:
            s3_key: S3 object key (e.g., "public_company_tracker/hkex_ipo_tracker/hkex_ipo_2025.csv")

        Returns:
            DataFrame with IPO data
        """
        try:
            logger.info(f"Reading IPO data from s3://{self.bucket_name}/{s3_key}")

            # Download file from S3
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            file_content = response['Body'].read()

            # Determine file type and read accordingly
            if s3_key.lower().endswith('.csv'):
                # Read CSV file (faster, no extra dependencies)
                df = pd.read_csv(BytesIO(file_content))
                logger.info(f"Read CSV file with {len(df)} rows")
            elif s3_key.lower().endswith(('.xlsx', '.xls')):
                # Read Excel file (requires openpyxl for .xlsx)
                df = pd.read_excel(BytesIO(file_content))
                logger.info(f"Read Excel file with {len(df)} rows")
            else:
                raise ValueError(f"Unsupported file format: {s3_key}. Use .csv, .xlsx, or .xls")

            logger.info(f"Successfully read {len(df)} rows from IPO tracker")
            return df

        except Exception as e:
            logger.error(f"Error reading IPO tracker from S3: {str(e)}")
            raise

    def process_ipo_data(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Process DataFrame and convert to list of dictionaries

        Args:
            df: Raw DataFrame from Excel file

        Returns:
            List of IPO records as dictionaries
        """
        # Replace NaN values with None for JSON serialization
        df = df.where(pd.notnull(df), None)

        # Convert DataFrame to list of dictionaries
        records = df.to_dict('records')

        # Process each record
        processed_records = []
        for record in records:
            processed = {}

            # Copy all fields
            for key, value in record.items():
                # Convert timestamps to ISO format strings
                if isinstance(value, pd.Timestamp):
                    processed[key] = value.isoformat()
                # Convert numpy/pandas types to native Python types
                elif pd.api.types.is_integer_dtype(type(value)):
                    processed[key] = int(value) if value is not None else None
                elif pd.api.types.is_float_dtype(type(value)):
                    processed[key] = float(value) if value is not None else None
                else:
                    processed[key] = value

            processed_records.append(processed)

        logger.info(f"Processed {len(processed_records)} IPO records")
        return processed_records

    def get_ipo_tracker_data(self, s3_key: str = None, use_cache: bool = True) -> Dict[str, Any]:
        """
        Get IPO tracker data from S3 with caching
        Supports both HTML and CSV/Excel formats

        Args:
            s3_key: S3 object key (optional, uses default if not provided)
            use_cache: If True, uses cached data if available (default: True)

        Returns:
            Dictionary with IPO data and metadata
        """
        global _ipo_cache

        # Default S3 key if not provided - prefer HTML report
        if s3_key is None:
            # Use latest HTML report by default
            s3_key = "public_company_tracker/hkex_ipo_tracker/hkex_ipo_report_20251116_222848.html"

        # Check cache if enabled
        if use_cache and _ipo_cache['data'] is not None and _ipo_cache['s3_key'] == s3_key:
            # Check if cache is still valid (5 minutes)
            if _ipo_cache['timestamp']:
                cache_age = (datetime.now() - _ipo_cache['timestamp']).total_seconds()
                if cache_age < 300:  # 5 minutes
                    logger.info(f"Returning cached IPO data (age: {cache_age:.1f}s)")
                    return _ipo_cache['data']

        logger.info(f"Cache miss or expired, fetching fresh data from S3")

        try:
            # Check if file is HTML or CSV/Excel
            if s3_key.lower().endswith('.html'):
                # Read HTML content directly
                html_content = self.read_html_from_s3(s3_key)

                result = {
                    "success": True,
                    "format": "html",
                    "html_content": html_content,
                    "source": f"s3://{self.bucket_name}/{s3_key}",
                    "last_updated": datetime.now().isoformat()
                }
            else:
                # Read data from S3 (CSV/Excel)
                df = self.read_ipo_tracker_from_s3(s3_key)

                # Process the data
                records = self.process_ipo_data(df)

                # Get column names for frontend reference
                columns = df.columns.tolist()

                result = {
                    "success": True,
                    "format": "table",
                    "count": len(records),
                    "columns": columns,
                    "data": records,
                    "source": f"s3://{self.bucket_name}/{s3_key}",
                    "last_updated": datetime.now().isoformat()
                }

            # Update cache
            _ipo_cache['data'] = result.copy()
            _ipo_cache['timestamp'] = datetime.now()
            _ipo_cache['s3_key'] = s3_key
            logger.info(f"Cached IPO data from {s3_key}")

            return result

        except Exception as e:
            logger.error(f"Error getting IPO tracker data: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "format": "table",
                "count": 0,
                "columns": [],
                "data": []
            }

    def get_latest_ipo_file(self, prefix: str = "public_company_tracker/hkex_ipo_tracker/", prefer_html: bool = True) -> str:
        """
        Find the latest IPO tracker file in S3

        Args:
            prefix: S3 prefix to search in
            prefer_html: If True, prefer HTML files over CSV/Excel files

        Returns:
            S3 key of the latest file
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )

            if 'Contents' not in response or len(response['Contents']) == 0:
                raise FileNotFoundError(f"No files found in s3://{self.bucket_name}/{prefix}")

            # Filter files based on preference
            files = response['Contents']

            if prefer_html:
                # First try to find HTML files
                html_files = [f for f in files if f['Key'].lower().endswith('.html')]
                if html_files:
                    html_files = sorted(html_files, key=lambda x: x['LastModified'], reverse=True)
                    latest_file = html_files[0]['Key']
                    logger.info(f"Found latest HTML IPO tracker file: {latest_file}")
                    return latest_file
                else:
                    logger.warning("No HTML files found, falling back to CSV/Excel")

            # Fallback to CSV/Excel files
            data_files = [f for f in files if f['Key'].lower().endswith(('.csv', '.xlsx', '.xls'))]
            if data_files:
                data_files = sorted(data_files, key=lambda x: x['LastModified'], reverse=True)
                latest_file = data_files[0]['Key']
                logger.info(f"Found latest data IPO tracker file: {latest_file}")
                return latest_file

            # If nothing found, return default
            raise FileNotFoundError(f"No suitable files found in {prefix}")

        except Exception as e:
            logger.error(f"Error finding latest IPO file: {str(e)}")
            # Return default CSV file if can't find latest
            return "public_company_tracker/hkex_ipo_tracker/hkex_ipo_2025_v20251113.csv"
