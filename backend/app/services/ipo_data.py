"""
IPO Data Service - Reads and processes IPO tracker data from S3
"""
import logging
import pandas as pd
import boto3
from io import BytesIO
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


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

    def read_ipo_tracker_from_s3(self, s3_key: str) -> pd.DataFrame:
        """
        Read Excel file from S3 and return as DataFrame

        Args:
            s3_key: S3 object key (e.g., "public_company_tracker/hkex_ipo_tracker/hkex_ipo_2025_v20251112.xlsx")

        Returns:
            DataFrame with IPO data
        """
        try:
            logger.info(f"Reading IPO data from s3://{self.bucket_name}/{s3_key}")

            # Download file from S3
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            file_content = response['Body'].read()

            # Read Excel file into DataFrame
            df = pd.read_excel(BytesIO(file_content))

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

    def get_ipo_tracker_data(self, s3_key: str = None) -> Dict[str, Any]:
        """
        Get IPO tracker data from S3

        Args:
            s3_key: S3 object key (optional, uses default if not provided)

        Returns:
            Dictionary with IPO data and metadata
        """
        # Default S3 key if not provided
        if s3_key is None:
            s3_key = "public_company_tracker/hkex_ipo_tracker/hkex_ipo_2025_v20251112.xlsx"

        try:
            # Read data from S3
            df = self.read_ipo_tracker_from_s3(s3_key)

            # Process the data
            records = self.process_ipo_data(df)

            # Get column names for frontend reference
            columns = df.columns.tolist()

            return {
                "success": True,
                "count": len(records),
                "columns": columns,
                "data": records,
                "source": f"s3://{self.bucket_name}/{s3_key}",
                "last_updated": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting IPO tracker data: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "count": 0,
                "columns": [],
                "data": []
            }

    def get_latest_ipo_file(self, prefix: str = "public_company_tracker/hkex_ipo_tracker/") -> str:
        """
        Find the latest IPO tracker file in S3

        Args:
            prefix: S3 prefix to search in

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

            # Sort by last modified date, get the most recent
            files = sorted(response['Contents'], key=lambda x: x['LastModified'], reverse=True)
            latest_file = files[0]['Key']

            logger.info(f"Found latest IPO tracker file: {latest_file}")
            return latest_file

        except Exception as e:
            logger.error(f"Error finding latest IPO file: {str(e)}")
            # Return default file if can't find latest
            return "public_company_tracker/hkex_ipo_tracker/hkex_ipo_2025_v20251112.xlsx"
