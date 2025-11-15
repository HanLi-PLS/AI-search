"""
AWS S3 storage utilities
"""
import boto3
from botocore.exceptions import ClientError
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class S3Storage:
    """Manage file storage in AWS S3"""

    def __init__(self, bucket_name: str, region_name: str = "us-west-2"):
        """
        Initialize S3 storage client

        Args:
            bucket_name: S3 bucket name
            region_name: AWS region
        """
        self.bucket_name = bucket_name
        self.region_name = region_name
        self.s3_client = boto3.client('s3', region_name=region_name)
        logger.info(f"S3 Storage initialized with bucket: {bucket_name}")

    def upload_file(self, file_path: Path, s3_key: str) -> bool:
        """
        Upload a file to S3

        Args:
            file_path: Local file path
            s3_key: S3 object key (path in bucket)

        Returns:
            True if successful, False otherwise
        """
        try:
            self.s3_client.upload_file(
                str(file_path),
                self.bucket_name,
                s3_key
            )
            logger.info(f"Uploaded {file_path} to s3://{self.bucket_name}/{s3_key}")
            return True

        except ClientError as e:
            logger.error(f"Error uploading to S3: {str(e)}")
            return False

    def download_file(self, s3_key: str, local_path: Path) -> bool:
        """
        Download a file from S3

        Args:
            s3_key: S3 object key
            local_path: Local file path to save to

        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure parent directory exists
            local_path.parent.mkdir(parents=True, exist_ok=True)

            self.s3_client.download_file(
                self.bucket_name,
                s3_key,
                str(local_path)
            )
            logger.info(f"Downloaded s3://{self.bucket_name}/{s3_key} to {local_path}")
            return True

        except ClientError as e:
            logger.error(f"Error downloading from S3: {str(e)}")
            return False

    def delete_file(self, s3_key: str) -> bool:
        """
        Delete a file from S3

        Args:
            s3_key: S3 object key

        Returns:
            True if successful, False otherwise
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            logger.info(f"Deleted s3://{self.bucket_name}/{s3_key}")
            return True

        except ClientError as e:
            logger.error(f"Error deleting from S3: {str(e)}")
            return False

    def file_exists(self, s3_key: str) -> bool:
        """
        Check if a file exists in S3

        Args:
            s3_key: S3 object key

        Returns:
            True if file exists, False otherwise
        """
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return True

        except ClientError:
            return False

    def list_files(self, prefix: str = "") -> list:
        """
        List files in S3 bucket with optional prefix

        Args:
            prefix: S3 key prefix to filter by

        Returns:
            List of S3 keys
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )

            if 'Contents' not in response:
                return []

            return [obj['Key'] for obj in response['Contents']]

        except ClientError as e:
            logger.error(f"Error listing S3 files: {str(e)}")
            return []

    def get_file_size(self, s3_key: str) -> Optional[int]:
        """
        Get file size in bytes

        Args:
            s3_key: S3 object key

        Returns:
            File size in bytes or None if error
        """
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return response['ContentLength']

        except ClientError as e:
            logger.error(f"Error getting file size: {str(e)}")
            return None

    def get_presigned_url(self, s3_key: str, expiration: int = 3600) -> Optional[str]:
        """
        Generate a presigned URL for downloading a file

        Args:
            s3_key: S3 object key
            expiration: URL expiration time in seconds (default 1 hour)

        Returns:
            Presigned URL or None if error
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=expiration
            )
            return url

        except ClientError as e:
            logger.error(f"Error generating presigned URL: {str(e)}")
            return None

    def copy_file(self, source_key: str, dest_key: str) -> bool:
        """
        Copy a file within S3

        Args:
            source_key: Source S3 object key
            dest_key: Destination S3 object key

        Returns:
            True if successful, False otherwise
        """
        try:
            copy_source = {
                'Bucket': self.bucket_name,
                'Key': source_key
            }
            self.s3_client.copy(copy_source, self.bucket_name, dest_key)
            logger.info(f"Copied s3://{self.bucket_name}/{source_key} to {dest_key}")
            return True

        except ClientError as e:
            logger.error(f"Error copying file in S3: {str(e)}")
            return False


# Global S3 storage instance
_s3_storage = None


def get_s3_storage(bucket_name: str = None, region_name: str = "us-west-2") -> Optional[S3Storage]:
    """
    Get or create the global S3 storage instance

    Args:
        bucket_name: S3 bucket name
        region_name: AWS region

    Returns:
        S3Storage instance or None if bucket not configured
    """
    global _s3_storage

    if bucket_name is None:
        return None

    if _s3_storage is None:
        _s3_storage = S3Storage(bucket_name, region_name)

    return _s3_storage
