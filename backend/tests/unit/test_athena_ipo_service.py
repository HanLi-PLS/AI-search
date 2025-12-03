"""
Unit tests for AthenaIPOService
Tests the AWS Athena integration for fetching IPO data from CapIQ financings table
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from backend.app.services.athena_ipo import AthenaIPOService, CURRENCY_NAME_TO_CODE


@pytest.mark.unit
@pytest.mark.athena
class TestAthenaIPOService:
    """Test suite for AthenaIPOService"""

    def test_currency_conversion_mappings(self):
        """Test currency name to code mappings"""
        assert CURRENCY_NAME_TO_CODE['Hong Kong Dollar'] == 'HKD'
        assert CURRENCY_NAME_TO_CODE['US Dollar'] == 'USD'
        assert CURRENCY_NAME_TO_CODE['Chinese Yuan'] == 'CNY'
        assert CURRENCY_NAME_TO_CODE['Renminbi'] == 'CNY'
        assert CURRENCY_NAME_TO_CODE.get('Unknown Currency') is None

    @patch('backend.app.services.athena_ipo.boto3')
    def test_init_success(self, mock_boto3):
        """Test successful initialization"""
        mock_client = Mock()
        mock_boto3.client.return_value = mock_client

        with patch('backend.app.services.athena_ipo.settings') as mock_settings:
            mock_settings.AWS_REGION = 'us-east-1'
            mock_settings.ATHENA_DATABASE = 'capiq'
            mock_settings.ATHENA_OUTPUT_LOCATION = 's3://test-bucket/athena-results/'

            service = AthenaIPOService()

            assert service.available is True
            assert service.database == 'capiq'
            assert service.output_location == 's3://test-bucket/athena-results/'
            mock_boto3.client.assert_called_once_with('athena', region_name='us-east-1')

    @patch('backend.app.services.athena_ipo.boto3')
    def test_init_no_output_location(self, mock_boto3):
        """Test initialization when output location is not configured"""
        with patch('backend.app.services.athena_ipo.settings') as mock_settings:
            mock_settings.AWS_REGION = 'us-east-1'
            mock_settings.ATHENA_DATABASE = 'capiq'
            mock_settings.ATHENA_OUTPUT_LOCATION = None

            service = AthenaIPOService()

            assert service.available is False

    @patch('backend.app.services.athena_ipo.boto3')
    def test_init_boto3_error(self, mock_boto3):
        """Test initialization when boto3 fails"""
        mock_boto3.client.side_effect = Exception("AWS credentials not found")

        service = AthenaIPOService()

        assert service.available is False

    def test_get_ipo_data_service_not_available(self):
        """Test getting IPO data when service is not available"""
        with patch('backend.app.services.athena_ipo.settings') as mock_settings:
            mock_settings.ATHENA_OUTPUT_LOCATION = None
            service = AthenaIPOService()

            result = service.get_ipo_data('1801', 'SEHK')

            assert result is None

    @patch('backend.app.services.athena_ipo.boto3')
    def test_get_ipo_data_success_hk_stock(self, mock_boto3, mock_athena_client):
        """Test successful IPO data retrieval for HK stock"""
        mock_boto3.client.return_value = mock_athena_client

        with patch('backend.app.services.athena_ipo.settings') as mock_settings:
            mock_settings.AWS_REGION = 'us-east-1'
            mock_settings.ATHENA_DATABASE = 'capiq'
            mock_settings.ATHENA_OUTPUT_LOCATION = 's3://test-bucket/athena-results/'

            service = AthenaIPOService()
            result = service.get_ipo_data('1801', 'SEHK')

        assert result is not None
        assert result['ticker'] == '1801'
        assert result['exchange'] == 'SEHK'
        assert result['ipo_listing_date'] == '2018-08-09'
        assert result['company'] == 'BeiGene, Ltd.'
        assert result['currency'] == 'HKD'
        assert result['ipo_price_original'] == 100.5
        assert result['ipo_price_usd'] == 12.8

    @patch('backend.app.services.athena_ipo.boto3')
    def test_get_ipo_data_ticker_normalization(self, mock_boto3, mock_athena_client):
        """Test that ticker is normalized (exchange suffix removed)"""
        mock_boto3.client.return_value = mock_athena_client

        with patch('backend.app.services.athena_ipo.settings') as mock_settings:
            mock_settings.AWS_REGION = 'us-east-1'
            mock_settings.ATHENA_DATABASE = 'capiq'
            mock_settings.ATHENA_OUTPUT_LOCATION = 's3://test-bucket/athena-results/'

            service = AthenaIPOService()

            # Test with .HK suffix - should be removed for query
            result = service.get_ipo_data('1801.HK', 'SEHK')

        assert result is not None
        # Verify the query was built with clean ticker
        call_args = mock_athena_client.start_query_execution.call_args
        query_string = call_args[1]['QueryString']
        assert "UPPER(tickersymbol)   = UPPER('1801')" in query_string

    @patch('backend.app.services.athena_ipo.boto3')
    def test_get_ipo_data_query_timeout(self, mock_boto3):
        """Test handling of query timeout"""
        mock_client = Mock()
        mock_client.start_query_execution.return_value = {'QueryExecutionId': 'test-id'}

        # Mock query status that never completes
        mock_client.get_query_execution.return_value = {
            'QueryExecution': {
                'Status': {'State': 'RUNNING'}
            }
        }

        mock_boto3.client.return_value = mock_client

        with patch('backend.app.services.athena_ipo.settings') as mock_settings:
            mock_settings.AWS_REGION = 'us-east-1'
            mock_settings.ATHENA_DATABASE = 'capiq'
            mock_settings.ATHENA_OUTPUT_LOCATION = 's3://test-bucket/athena-results/'

            service = AthenaIPOService()

            # Patch time.sleep to avoid actual delay in test
            with patch('backend.app.services.athena_ipo.time.sleep'):
                result = service.get_ipo_data('1801', 'SEHK')

        assert result is None

    @patch('backend.app.services.athena_ipo.boto3')
    def test_get_ipo_data_query_failed(self, mock_boto3):
        """Test handling of failed query"""
        mock_client = Mock()
        mock_client.start_query_execution.return_value = {'QueryExecutionId': 'test-id'}
        mock_client.get_query_execution.return_value = {
            'QueryExecution': {
                'Status': {
                    'State': 'FAILED',
                    'StateChangeReason': 'Syntax error in query'
                }
            }
        }

        mock_boto3.client.return_value = mock_client

        with patch('backend.app.services.athena_ipo.settings') as mock_settings:
            mock_settings.AWS_REGION = 'us-east-1'
            mock_settings.ATHENA_DATABASE = 'capiq'
            mock_settings.ATHENA_OUTPUT_LOCATION = 's3://test-bucket/athena-results/'

            service = AthenaIPOService()
            result = service.get_ipo_data('1801', 'SEHK')

        assert result is None

    @patch('backend.app.services.athena_ipo.boto3')
    def test_get_ipo_data_no_results(self, mock_boto3):
        """Test handling when no IPO data is found"""
        mock_client = Mock()
        mock_client.start_query_execution.return_value = {'QueryExecutionId': 'test-id'}
        mock_client.get_query_execution.return_value = {
            'QueryExecution': {
                'Status': {'State': 'SUCCEEDED'}
            }
        }
        # Only header row, no data
        mock_client.get_query_results.return_value = {
            'ResultSet': {
                'Rows': [
                    {'Data': []}  # Header only
                ]
            }
        }

        mock_boto3.client.return_value = mock_client

        with patch('backend.app.services.athena_ipo.settings') as mock_settings:
            mock_settings.AWS_REGION = 'us-east-1'
            mock_settings.ATHENA_DATABASE = 'capiq'
            mock_settings.ATHENA_OUTPUT_LOCATION = 's3://test-bucket/athena-results/'

            service = AthenaIPOService()
            result = service.get_ipo_data('UNKNOWN', 'SEHK')

        assert result is None

    @patch('backend.app.services.athena_ipo.boto3')
    def test_get_ipo_data_sehk_date_adjustment(self, mock_boto3, mock_athena_client):
        """Test that SEHK IPO dates are adjusted by +1 day"""
        mock_boto3.client.return_value = mock_athena_client

        with patch('backend.app.services.athena_ipo.settings') as mock_settings:
            mock_settings.AWS_REGION = 'us-east-1'
            mock_settings.ATHENA_DATABASE = 'capiq'
            mock_settings.ATHENA_OUTPUT_LOCATION = 's3://test-bucket/athena-results/'

            service = AthenaIPOService()

            # Check the query includes date adjustment logic
            result = service.get_ipo_data('1801', 'SEHK')

            call_args = mock_athena_client.start_query_execution.call_args
            query_string = call_args[1]['QueryString']

            # Should have CASE WHEN for SEHK with date_add
            assert 'CASE' in query_string
            assert 'UPPER(exchangesymbol) = \'SEHK\'' in query_string
            assert 'date_add' in query_string

    @patch('backend.app.services.athena_ipo.boto3')
    def test_get_ipo_data_us_stock(self, mock_boto3):
        """Test IPO data retrieval for US stock (no date adjustment)"""
        mock_client = Mock()
        mock_client.start_query_execution.return_value = {'QueryExecutionId': 'test-id'}
        mock_client.get_query_execution.return_value = {
            'QueryExecution': {'Status': {'State': 'SUCCEEDED'}}
        }
        mock_client.get_query_results.return_value = {
            'ResultSet': {
                'Rows': [
                    {'Data': []},  # Header
                    {
                        'Data': [
                            {'VarCharValue': 'ZBIO Holdings Inc'},
                            {'VarCharValue': 'ZBIO'},
                            {'VarCharValue': 'NASDAQ'},
                            {'VarCharValue': '2023-06-15'},
                            {'VarCharValue': '10000000.0'},
                            {'VarCharValue': '5.0'},
                            {'VarCharValue': '1.0'},
                            {'VarCharValue': '5.0'},
                            {'VarCharValue': 'US Dollar'}
                        ]
                    }
                ]
            }
        }

        mock_boto3.client.return_value = mock_client

        with patch('backend.app.services.athena_ipo.settings') as mock_settings:
            mock_settings.AWS_REGION = 'us-east-1'
            mock_settings.ATHENA_DATABASE = 'capiq'
            mock_settings.ATHENA_OUTPUT_LOCATION = 's3://test-bucket/athena-results/'

            service = AthenaIPOService()
            result = service.get_ipo_data('ZBIO', 'NASDAQ')

        assert result is not None
        assert result['ticker'] == 'ZBIO'
        assert result['exchange'] == 'NASDAQ'
        assert result['currency'] == 'USD'

    @patch('backend.app.services.athena_ipo.boto3')
    def test_get_ipo_data_null_values(self, mock_boto3):
        """Test handling of null values in IPO data"""
        mock_client = Mock()
        mock_client.start_query_execution.return_value = {'QueryExecutionId': 'test-id'}
        mock_client.get_query_execution.return_value = {
            'QueryExecution': {'Status': {'State': 'SUCCEEDED'}}
        }
        # Data with some null values
        mock_client.get_query_results.return_value = {
            'ResultSet': {
                'Rows': [
                    {'Data': []},  # Header
                    {
                        'Data': [
                            {'VarCharValue': 'Test Company'},
                            {'VarCharValue': '1234'},
                            {'VarCharValue': 'SEHK'},
                            {'VarCharValue': '2023-01-01'},
                            {},  # No offering_size
                            {},  # No ipo_price_original
                            {},  # No exchange_rate
                            {},  # No ipo_price_usd
                            {}   # No currency
                        ]
                    }
                ]
            }
        }

        mock_boto3.client.return_value = mock_client

        with patch('backend.app.services.athena_ipo.settings') as mock_settings:
            mock_settings.AWS_REGION = 'us-east-1'
            mock_settings.ATHENA_DATABASE = 'capiq'
            mock_settings.ATHENA_OUTPUT_LOCATION = 's3://test-bucket/athena-results/'

            service = AthenaIPOService()
            result = service.get_ipo_data('1234', 'SEHK')

        assert result is not None
        assert result['ticker'] == '1234'
        assert result['offering_size'] is None
        assert result['ipo_price_original'] is None
        assert result['currency'] is None

    def test_get_athena_ipo_service_singleton(self):
        """Test that get_athena_ipo_service returns singleton instance"""
        from backend.app.services.athena_ipo import get_athena_ipo_service, _athena_ipo_service

        # Reset global instance
        import backend.app.services.athena_ipo as module
        module._athena_ipo_service = None

        # Get service twice
        service1 = get_athena_ipo_service()
        service2 = get_athena_ipo_service()

        # Should be same instance
        assert service1 is service2

    @patch('backend.app.services.athena_ipo.boto3')
    def test_query_construction(self, mock_boto3, mock_athena_client):
        """Test that SQL query is constructed correctly"""
        mock_boto3.client.return_value = mock_athena_client

        with patch('backend.app.services.athena_ipo.settings') as mock_settings:
            mock_settings.AWS_REGION = 'us-east-1'
            mock_settings.ATHENA_DATABASE = 'capiq'
            mock_settings.ATHENA_OUTPUT_LOCATION = 's3://test-bucket/athena-results/'

            service = AthenaIPOService()
            service.get_ipo_data('1801', 'SEHK')

            # Verify query was called
            call_args = mock_athena_client.start_query_execution.call_args
            query_string = call_args[1]['QueryString']

            # Check key parts of query
            assert 'capiq__latest_financings' in query_string
            assert "transactionidtypename = 'Public Offering'" in query_string
            assert "primaryfeature = 'IPO'" in query_string
            assert "UPPER(tickersymbol)   = UPPER('1801')" in query_string
            assert "UPPER(exchangesymbol) = UPPER('SEHK')" in query_string
            assert 'LIMIT 1' in query_string
