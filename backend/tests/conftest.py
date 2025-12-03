"""
Pytest configuration and shared fixtures
"""
import pytest
import os
import sys
from datetime import date, datetime
from typing import Dict, Any, List
from unittest.mock import Mock, MagicMock

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


@pytest.fixture
def mock_stock_data() -> Dict[str, Any]:
    """Mock stock data for testing"""
    return {
        'ticker': '1801.HK',
        'name': 'BeiGene',
        'current_price': 100.50,
        'previous_close': 95.00,
        'open': 96.00,
        'high': 102.00,
        'low': 95.50,
        'volume': 1000000,
        'change': 5.50,
        'change_percent': 5.79,
        'intraday_change': 4.50,
        'intraday_change_percent': 4.69,
        'trade_date': '2025-01-15',
        'market_cap': 15000000000,
        'ps_ratio': 8.5,
        'ipo_date': '2018-08-08'
    }


@pytest.fixture
def mock_big_mover_stock() -> Dict[str, Any]:
    """Mock stock data with significant price movement (>= 10%)"""
    return {
        'ticker': '2359.HK',
        'name': 'WuXi Biologics',
        'current_price': 55.00,
        'previous_close': 50.00,
        'open': 51.00,
        'high': 56.00,
        'low': 50.50,
        'volume': 5000000,
        'change': 5.00,
        'change_percent': 10.00,
        'intraday_change': 4.00,
        'intraday_change_percent': 7.84,
        'trade_date': '2025-01-15'
    }


@pytest.fixture
def mock_historical_data() -> List[Dict[str, Any]]:
    """Mock historical stock data"""
    return [
        {
            'ticker': '1801.HK',
            'ts_code': '01801.HK',
            'trade_date': '2025-01-15',
            'open': 96.00,
            'high': 102.00,
            'low': 95.50,
            'close': 100.50,
            'pre_close': 95.00,
            'volume': 1000000,
            'amount': 100000000,
            'change': 5.50,
            'pct_change': 5.79,
            'data_source': 'Tushare Pro'
        },
        {
            'ticker': '1801.HK',
            'ts_code': '01801.HK',
            'trade_date': '2025-01-14',
            'open': 94.00,
            'high': 96.00,
            'low': 93.00,
            'close': 95.00,
            'pre_close': 93.50,
            'volume': 800000,
            'amount': 76000000,
            'change': 1.50,
            'pct_change': 1.60,
            'data_source': 'Tushare Pro'
        }
    ]


@pytest.fixture
def mock_ipo_data() -> Dict[str, Any]:
    """Mock IPO data from Athena"""
    return {
        'company': 'BeiGene, Ltd.',
        'ticker': '1801',
        'exchange': 'SEHK',
        'ipo_listing_date': '2018-08-09',
        'offering_size': 903000000.0,
        'ipo_price_original': 100.5,
        'exchange_rate': 7.8492,
        'ipo_price_usd': 12.8,
        'currency': 'HKD'
    }


@pytest.fixture
def mock_watchlist_items() -> List[Dict[str, Any]]:
    """Mock watchlist items"""
    return [
        {
            'ticker': 'ZBIO',
            'name': 'ZBIO Holdings Inc',
            'market': 'US',
            'current_price': 2.45,
            'change_percent': -3.54,
            'added_at': '2025-01-10T10:00:00'
        },
        {
            'ticker': '1801.HK',
            'name': 'BeiGene',
            'market': 'HK',
            'current_price': 100.50,
            'change_percent': 5.79,
            'added_at': '2025-01-12T14:30:00'
        }
    ]


@pytest.fixture
def mock_tushare_response():
    """Mock Tushare API response"""
    mock_df = Mock()
    mock_df.empty = False
    mock_df.to_dict.return_value = [
        {
            'trade_date': '20250115',
            'open': 96.0,
            'high': 102.0,
            'low': 95.5,
            'close': 100.5,
            'pre_close': 95.0,
            'vol': 1000000,
            'amount': 100000,
            'change': 5.5,
            'pct_chg': 5.79
        }
    ]
    return mock_df


@pytest.fixture
def mock_athena_client():
    """Mock boto3 Athena client"""
    client = MagicMock()

    # Mock successful query execution
    client.start_query_execution.return_value = {
        'QueryExecutionId': 'test-query-id-123'
    }

    # Mock query status - succeeded
    client.get_query_execution.return_value = {
        'QueryExecution': {
            'Status': {
                'State': 'SUCCEEDED'
            }
        }
    }

    # Mock query results
    client.get_query_results.return_value = {
        'ResultSet': {
            'Rows': [
                # Header row
                {'Data': []},
                # Data row
                {
                    'Data': [
                        {'VarCharValue': 'BeiGene, Ltd.'},
                        {'VarCharValue': '1801'},
                        {'VarCharValue': 'SEHK'},
                        {'VarCharValue': '2018-08-09'},
                        {'VarCharValue': '903000000.0'},
                        {'VarCharValue': '100.5'},
                        {'VarCharValue': '7.8492'},
                        {'VarCharValue': '12.8'},
                        {'VarCharValue': 'Hong Kong Dollar'}
                    ]
                }
            ]
        }
    }

    return client


@pytest.fixture
def mock_db_session():
    """Mock SQLAlchemy database session"""
    session = MagicMock()
    session.query.return_value = session
    session.filter.return_value = session
    session.order_by.return_value = session
    session.limit.return_value = session
    session.all.return_value = []
    session.scalar.return_value = None
    return session


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response for news analysis"""
    return {
        'choices': [
            {
                'message': {
                    'content': 'The stock price surged following positive Phase 3 clinical trial results announced today.'
                }
            }
        ]
    }


@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment variables before each test"""
    # Store original values
    original_env = os.environ.copy()

    # Set test environment variables
    os.environ['TESTING'] = 'true'
    os.environ['TUSHARE_API_TOKEN'] = 'test-token'
    os.environ['FINNHUB_API_KEY'] = 'test-api-key'

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)
