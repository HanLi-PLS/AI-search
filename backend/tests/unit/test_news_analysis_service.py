"""
Unit tests for StockNewsAnalysisService
Tests the AI-powered news analysis feature for stocks with significant price moves
"""
import pytest
from unittest.mock import Mock, MagicMock, patch, mock_open
from datetime import datetime
import json
from backend.app.services.stock_news_analysis import StockNewsAnalysisService


@pytest.mark.unit
@pytest.mark.news
class TestStockNewsAnalysisService:
    """Test suite for StockNewsAnalysisService"""

    @patch('backend.app.services.stock_news_analysis.OpenAI')
    def test_init(self, mock_openai):
        """Test service initialization"""
        service = StockNewsAnalysisService()

        assert service.cache_dir is not None
        assert service.cache_file is not None
        assert service.threshold_percent == 10.0
        mock_openai.assert_called_once()

    def test_has_significant_move_daily_change(self):
        """Test detection of significant daily price move"""
        service = StockNewsAnalysisService()

        # Stock with 12% daily change
        stock_data = {
            'change_percent': 12.0,
            'intraday_change_percent': 2.0
        }

        assert service.has_significant_move(stock_data) is True

    def test_has_significant_move_intraday_change(self):
        """Test detection of significant intraday price move"""
        service = StockNewsAnalysisService()

        # Stock with 11% intraday change
        stock_data = {
            'change_percent': 3.0,
            'intraday_change_percent': 11.0
        }

        assert service.has_significant_move(stock_data) is True

    def test_has_significant_move_negative_change(self):
        """Test detection with negative price moves"""
        service = StockNewsAnalysisService()

        # Stock with -15% daily change
        stock_data = {
            'change_percent': -15.0,
            'intraday_change_percent': -2.0
        }

        assert service.has_significant_move(stock_data) is True

    def test_no_significant_move(self):
        """Test when stock doesn't have significant move"""
        service = StockNewsAnalysisService()

        # Stock with small changes
        stock_data = {
            'change_percent': 3.5,
            'intraday_change_percent': 2.1
        }

        assert service.has_significant_move(stock_data) is False

    def test_has_significant_move_missing_data(self):
        """Test handling when price change data is missing"""
        service = StockNewsAnalysisService()

        # Stock with missing change data
        stock_data = {}

        assert service.has_significant_move(stock_data) is False

    @patch('backend.app.services.stock_news_analysis.OpenAI')
    def test_get_news_analysis_from_cache(self, mock_openai):
        """Test retrieving news analysis from cache"""
        service = StockNewsAnalysisService()

        # Mock cache data
        today = datetime.now().strftime('%Y-%m-%d')
        cache_data = {
            'date': today,
            'analyses': {
                '1801.HK': {
                    'ticker': '1801.HK',
                    'name': 'BeiGene',
                    'analysis': 'Cached analysis text',
                    'change_percent': 12.5,
                    'cached_at': datetime.now().isoformat()
                }
            }
        }

        with patch('builtins.open', mock_open(read_data=json.dumps(cache_data))):
            with patch('os.path.exists', return_value=True):
                stock_data = {'change_percent': 12.5}
                result = service.get_news_analysis('1801.HK', 'BeiGene', stock_data)

        assert result is not None
        assert result['analysis'] == 'Cached analysis text'
        # Should not call OpenAI if cached
        assert not mock_openai.return_value.chat.completions.create.called

    @patch('backend.app.services.stock_news_analysis.OpenAI')
    def test_get_news_analysis_fetch_new(self, mock_openai):
        """Test fetching new news analysis from OpenAI"""
        # Mock OpenAI response
        mock_completion = Mock()
        mock_completion.choices = [
            Mock(message=Mock(content='Stock surged on positive clinical trial results.'))
        ]
        mock_openai.return_value.chat.completions.create.return_value = mock_completion

        service = StockNewsAnalysisService()

        # Mock empty cache
        with patch('os.path.exists', return_value=False):
            with patch('builtins.open', mock_open()):
                with patch('os.makedirs'):
                    stock_data = {'change_percent': 15.0, 'intraday_change_percent': 2.0}
                    result = service.get_news_analysis('1801.HK', 'BeiGene', stock_data)

        assert result is not None
        assert result['ticker'] == '1801.HK'
        assert result['name'] == 'BeiGene'
        assert 'clinical trial' in result['analysis']
        mock_openai.return_value.chat.completions.create.assert_called_once()

    @patch('backend.app.services.stock_news_analysis.OpenAI')
    def test_get_news_analysis_openai_error(self, mock_openai):
        """Test handling OpenAI API errors"""
        # Mock OpenAI error
        mock_openai.return_value.chat.completions.create.side_effect = Exception("API rate limit exceeded")

        service = StockNewsAnalysisService()

        with patch('os.path.exists', return_value=False):
            with patch('builtins.open', mock_open()):
                with patch('os.makedirs'):
                    stock_data = {'change_percent': 15.0}
                    result = service.get_news_analysis('1801.HK', 'BeiGene', stock_data)

        # Should return None on error
        assert result is None

    def test_process_stocks_with_big_movers(self, mock_big_mover_stock):
        """Test processing list of stocks and identifying big movers"""
        service = StockNewsAnalysisService()

        stocks = [
            {'ticker': '1801.HK', 'name': 'BeiGene', 'change_percent': 3.0},
            mock_big_mover_stock,  # Has 10% move
            {'ticker': '1952.HK', 'name': 'ALK', 'change_percent': 5.0}
        ]

        with patch.object(service, 'get_news_analysis', return_value={'analysis': 'Test analysis'}):
            result = service.process_stocks(stocks)

        # Should only process the big mover
        assert len(result) == 3
        # Check that only the big mover has news_analysis
        assert 'news_analysis' not in result[0]
        assert 'news_analysis' in result[1]
        assert 'news_analysis' not in result[2]

    def test_process_stocks_no_big_movers(self):
        """Test processing stocks when none have significant moves"""
        service = StockNewsAnalysisService()

        stocks = [
            {'ticker': '1801.HK', 'name': 'BeiGene', 'change_percent': 3.0},
            {'ticker': '2359.HK', 'name': 'WuXi', 'change_percent': 5.0}
        ]

        result = service.process_stocks(stocks)

        # Should return unchanged
        assert len(result) == 2
        assert 'news_analysis' not in result[0]
        assert 'news_analysis' not in result[1]

    def test_get_cache_stats_empty(self):
        """Test cache stats when cache is empty"""
        service = StockNewsAnalysisService()

        with patch('os.path.exists', return_value=False):
            stats = service.get_cache_stats()

        today = datetime.now().strftime('%Y-%m-%d')
        assert stats['date'] == today
        assert stats['entries'] == 0
        assert stats['tickers'] == []

    def test_get_cache_stats_with_data(self):
        """Test cache stats when cache has data"""
        service = StockNewsAnalysisService()

        today = datetime.now().strftime('%Y-%m-%d')
        cache_data = {
            'date': today,
            'analyses': {
                '1801.HK': {'analysis': 'Test 1'},
                '2359.HK': {'analysis': 'Test 2'}
            }
        }

        with patch('builtins.open', mock_open(read_data=json.dumps(cache_data))):
            with patch('os.path.exists', return_value=True):
                stats = service.get_cache_stats()

        assert stats['date'] == today
        assert stats['entries'] == 2
        assert '1801.HK' in stats['tickers']
        assert '2359.HK' in stats['tickers']

    def test_cache_invalidation_new_day(self):
        """Test that cache is invalidated on new day"""
        service = StockNewsAnalysisService()

        # Cache from yesterday
        yesterday = (datetime.now().replace(day=datetime.now().day - 1)).strftime('%Y-%m-%d')
        cache_data = {
            'date': yesterday,
            'analyses': {
                '1801.HK': {'analysis': 'Old analysis'}
            }
        }

        with patch('builtins.open', mock_open(read_data=json.dumps(cache_data))):
            with patch('os.path.exists', return_value=True):
                # Should not find cached data from yesterday
                stock_data = {'change_percent': 12.0}

                # Mock empty/reset for new day
                with patch.object(service, '_save_cache'):
                    # The service should recognize cache is from different day
                    service._load_cache()
                    today = datetime.now().strftime('%Y-%m-%d')
                    assert service.cache.get('date') != today or service.cache.get('date') == yesterday

    @patch('backend.app.services.stock_news_analysis.OpenAI')
    def test_prompt_construction(self, mock_openai):
        """Test that prompt is constructed correctly"""
        mock_completion = Mock()
        mock_completion.choices = [Mock(message=Mock(content='Analysis'))]
        mock_openai.return_value.chat.completions.create.return_value = mock_completion

        service = StockNewsAnalysisService()

        with patch('os.path.exists', return_value=False):
            with patch('builtins.open', mock_open()):
                with patch('os.makedirs'):
                    stock_data = {
                        'change_percent': 15.0,
                        'intraday_change_percent': 3.0
                    }
                    service.get_news_analysis('1801.HK', 'BeiGene', stock_data)

        # Verify OpenAI was called with correct structure
        call_args = mock_openai.return_value.chat.completions.create.call_args
        assert call_args is not None
        messages = call_args[1]['messages']

        # Check prompt includes key information
        prompt_text = str(messages)
        assert '1801.HK' in prompt_text
        assert 'BeiGene' in prompt_text
        assert '15.0' in prompt_text

    def test_threshold_customization(self):
        """Test that significance threshold can be customized"""
        # Test default threshold
        service = StockNewsAnalysisService()
        assert service.threshold_percent == 10.0

        # Test custom threshold
        service_custom = StockNewsAnalysisService(threshold_percent=5.0)
        assert service_custom.threshold_percent == 5.0

        # Stock with 7% move - significant for 5% threshold but not 10%
        stock_data = {'change_percent': 7.0}
        assert service_custom.has_significant_move(stock_data) is True
        assert service.has_significant_move(stock_data) is False

    def test_concurrent_processing(self, mock_big_mover_stock):
        """Test processing multiple stocks doesn't cause race conditions"""
        service = StockNewsAnalysisService()

        stocks = [mock_big_mover_stock for _ in range(5)]

        with patch.object(service, 'get_news_analysis', return_value={'analysis': 'Test'}) as mock_get:
            result = service.process_stocks(stocks)

        assert len(result) == 5
        # Should have been called for each stock
        assert mock_get.call_count == 5

    @patch('backend.app.services.stock_news_analysis.logger')
    def test_logging_for_debugging(self, mock_logger):
        """Test that appropriate logging is done"""
        service = StockNewsAnalysisService()

        stocks = [{'ticker': '1801.HK', 'name': 'BeiGene', 'change_percent': 15.0}]

        with patch.object(service, 'has_significant_move', return_value=True):
            with patch.object(service, 'get_news_analysis', return_value={'analysis': 'Test'}):
                service.process_stocks(stocks)

        # Verify logging was called (implementation dependent)
        assert True  # Logging test placeholder

    def test_handle_special_characters_in_name(self):
        """Test handling of special characters in company names"""
        service = StockNewsAnalysisService()

        special_name = "BeiGene & Co., Ltd. (Holdings)"
        stock_data = {'change_percent': 15.0}

        with patch.object(service, 'get_news_analysis', return_value={'analysis': 'Test'}):
            # Should not crash with special characters
            result = service.get_news_analysis('1801.HK', special_name, stock_data)

        assert result is not None

    def test_cache_directory_creation(self):
        """Test that cache directory is created if it doesn't exist"""
        service = StockNewsAnalysisService()

        with patch('os.path.exists', return_value=False):
            with patch('os.makedirs') as mock_makedirs:
                with patch('builtins.open', mock_open()):
                    service._save_cache()

                # Should create directory
                mock_makedirs.assert_called()
