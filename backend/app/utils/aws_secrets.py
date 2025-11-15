"""
AWS Secrets Manager integration
"""
import boto3
import ast
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger(__name__)


def get_key(secret_name: str, region_name: str) -> str:
    """
    Retrieve a secret from AWS Secrets Manager

    Args:
        secret_name: Name of the secret in AWS Secrets Manager
        region_name: AWS region where the secret is stored

    Returns:
        The secret value

    Raises:
        ClientError: If the secret cannot be retrieved
    """
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        logger.error(f"Error retrieving secret {secret_name}: {str(e)}")
        raise e

    secret = get_secret_value_response['SecretString']
    key = ast.literal_eval(secret)['key']

    return key
