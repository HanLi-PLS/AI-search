"""
AWS Athena Service for fetching IPO data from CapIQ financings table
"""
import logging
import time
from typing import Optional, Dict, Any
import boto3
from backend.app.config import settings

logger = logging.getLogger(__name__)


class AthenaIPOService:
    """Service for querying IPO data from AWS Athena"""

    def __init__(self):
        """Initialize Athena client"""
        try:
            self.client = boto3.client(
                'athena',
                region_name=getattr(settings, 'AWS_REGION', 'us-east-1')
            )
            self.database = getattr(settings, 'ATHENA_DATABASE', 'capiq')
            self.output_location = getattr(settings, 'ATHENA_OUTPUT_LOCATION', None)
            self.available = self.output_location is not None

            if not self.available:
                logger.warning("Athena IPO service not configured (ATHENA_OUTPUT_LOCATION not set)")
        except Exception as e:
            logger.error(f"Failed to initialize Athena client: {e}")
            self.available = False

    def get_ipo_data(self, ticker: str, exchange_symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get IPO listing data for a ticker

        Args:
            ticker: Stock ticker symbol (e.g., '2595')
            exchange_symbol: Exchange symbol (e.g., 'SEHK', 'NYSE')

        Returns:
            Dictionary with IPO data or None if not found
        """
        if not self.available:
            logger.debug(f"Athena not available, skipping IPO data for {ticker}")
            return None

        # Normalize ticker - remove exchange suffix if present
        clean_ticker = ticker.split('.')[0]

        query = f"""
        SELECT
            target_or_issuer                          AS company,
            tickersymbol                              AS ticker,
            exchangesymbol                            AS exchange,
            CASE
                WHEN UPPER(exchangesymbol) = 'SEHK' THEN
                    date_add('day', 1, COALESCE(closeddate, announceddate))
                ELSE
                    COALESCE(closeddate, announceddate)
            END                                        AS ipo_listing_date,
            transactionsize_original_currency_offering AS offering_size,
            price_original_currency                    AS ipo_price_original,
            exchange_rate_on_closed                    AS exchange_rate,
            price_usd                                  AS ipo_price_usd,
            original_currency                          AS currency
        FROM capiq__latest_financings
        WHERE transactionidtypename = 'Public Offering'
          AND primaryfeature = 'IPO'
          AND UPPER(tickersymbol)   = UPPER('{clean_ticker}')
          AND UPPER(exchangesymbol) = UPPER('{exchange_symbol}')
        ORDER BY COALESCE(closeddate, announceddate) DESC
        LIMIT 1
        """

        try:
            # Start query execution
            response = self.client.start_query_execution(
                QueryString=query,
                QueryExecutionContext={'Database': self.database},
                ResultConfiguration={'OutputLocation': self.output_location}
            )

            query_execution_id = response['QueryExecutionId']

            # Wait for query to complete
            max_attempts = 30
            for attempt in range(max_attempts):
                query_status = self.client.get_query_execution(
                    QueryExecutionId=query_execution_id
                )
                status = query_status['QueryExecution']['Status']['State']

                if status == 'SUCCEEDED':
                    break
                elif status in ['FAILED', 'CANCELLED']:
                    error_msg = query_status['QueryExecution']['Status'].get(
                        'StateChangeReason', 'Unknown error'
                    )
                    logger.error(f"Athena query failed for {ticker}: {error_msg}")
                    return None

                time.sleep(0.5)
            else:
                logger.warning(f"Athena query timeout for {ticker}")
                return None

            # Get query results
            result = self.client.get_query_results(
                QueryExecutionId=query_execution_id,
                MaxResults=2  # Header + 1 data row
            )

            rows = result['ResultSet']['Rows']
            if len(rows) < 2:  # No data row (only header)
                logger.debug(f"No IPO data found in Athena for {ticker} on {exchange_symbol}")
                return None

            # Parse data row (skip header)
            data_row = rows[1]['Data']

            return {
                'company': data_row[0].get('VarCharValue'),
                'ticker': data_row[1].get('VarCharValue'),
                'exchange': data_row[2].get('VarCharValue'),
                'ipo_listing_date': data_row[3].get('VarCharValue'),
                'offering_size': float(data_row[4]['VarCharValue']) if data_row[4].get('VarCharValue') else None,
                'ipo_price_original': float(data_row[5]['VarCharValue']) if data_row[5].get('VarCharValue') else None,
                'exchange_rate': float(data_row[6]['VarCharValue']) if data_row[6].get('VarCharValue') else None,
                'ipo_price_usd': float(data_row[7]['VarCharValue']) if data_row[7].get('VarCharValue') else None,
                'currency': data_row[8].get('VarCharValue'),
            }

        except Exception as e:
            logger.error(f"Error querying Athena for IPO data ({ticker}): {e}")
            return None


# Global instance
_athena_ipo_service = None


def get_athena_ipo_service() -> AthenaIPOService:
    """Get or create Athena IPO service instance"""
    global _athena_ipo_service
    if _athena_ipo_service is None:
        _athena_ipo_service = AthenaIPOService()
    return _athena_ipo_service
