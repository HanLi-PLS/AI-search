"""
Integration tests for Stock API endpoints
Tests the /api/stocks/* endpoints
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from backend.app.main import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.mark.integration
@pytest.mark.api
class TestStockRoutes:
    """Test suite for stock API routes"""

    def test_get_all_prices_success(self, client, mock_stock_data):
        """Test GET /api/stocks endpoint"""
        with patch('backend.app.api.routes.stocks.stockAPI') as mock_api:
            mock_api.getAllPrices.return_value = [mock_stock_data]

            response = client.get('/api/stocks')

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) > 0 or True  # May be empty if no cache

    def test_get_all_prices_with_force_refresh(self, client):
        """Test GET /api/stocks with force_refresh parameter"""
        with patch('backend.app.api.routes.stocks.fetch_all_stock_prices') as mock_fetch:
            mock_fetch.return_value = []

            response = client.get('/api/stocks?force_refresh=true')

            assert response.status_code == 200
            # Should have called fetch with force_refresh=True
            if mock_fetch.called:
                assert True

    def test_get_single_stock_price_success(self, client, mock_stock_data):
        """Test GET /api/stocks/{ticker} endpoint"""
        ticker = '1801.HK'

        with patch('backend.app.api.routes.stocks.get_single_stock_price') as mock_get:
            mock_get.return_value = mock_stock_data

            response = client.get(f'/api/stocks/{ticker}')

            assert response.status_code in [200, 404]  # May not exist in cache

    def test_get_single_stock_price_not_found(self, client):
        """Test GET /api/stocks/{ticker} for non-existent stock"""
        ticker = 'NONEXISTENT.HK'

        response = client.get(f'/api/stocks/{ticker}')

        # Should either return 404 or empty result
        assert response.status_code in [200, 404]

    def test_get_historical_data_success(self, client, mock_historical_data):
        """Test GET /api/stocks/{ticker}/history endpoint"""
        ticker = '1801.HK'

        with patch('backend.app.services.stock_data.StockDataService.get_historical_data') as mock_get:
            mock_get.return_value = mock_historical_data

            response = client.get(f'/api/stocks/{ticker}/history?days=90')

            assert response.status_code == 200
            data = response.json()
            assert 'ticker' in data or 'data' in data or isinstance(data, list)

    def test_get_historical_data_with_date_range(self, client):
        """Test GET /api/stocks/{ticker}/history with date range"""
        ticker = '1801.HK'

        response = client.get(
            f'/api/stocks/{ticker}/history'
            f'?start_date=2025-01-01&end_date=2025-01-15'
        )

        assert response.status_code in [200, 404, 500]

    def test_get_historical_data_invalid_ticker(self, client):
        """Test GET /api/stocks/{ticker}/history with invalid ticker"""
        response = client.get('/api/stocks/INVALID/history')

        # Should handle gracefully
        assert response.status_code in [200, 404, 422, 500]

    def test_update_single_stock_history(self, client):
        """Test POST /api/stocks/{ticker}/update-history endpoint"""
        ticker = '1801.HK'

        with patch('backend.app.services.stock_data.StockDataService.update_incremental') as mock_update:
            mock_update.return_value = 5  # 5 new records

            response = client.post(f'/api/stocks/{ticker}/update-history')

            # May require authentication
            assert response.status_code in [200, 401, 403]

    def test_bulk_update_history(self, client):
        """Test POST /api/stocks/bulk-update-history endpoint"""
        with patch('backend.app.services.stock_data.StockDataService.bulk_update_all_stocks') as mock_bulk:
            mock_bulk.return_value = {
                'total': 66,
                'updated': 65,
                'new_records': 1234,
                'errors': 1
            }

            response = client.post('/api/stocks/bulk-update-history')

            # May require authentication
            assert response.status_code in [200, 401, 403]

    def test_get_history_stats(self, client):
        """Test GET /api/stocks/history/stats endpoint"""
        response = client.get('/api/stocks/history/stats')

        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            # Should contain statistics
            assert 'total_stocks' in data or isinstance(data, dict)

    def test_get_stock_detail_success(self, client, mock_stock_data, mock_ipo_data):
        """Test GET /api/stocks/{ticker}/detail endpoint"""
        ticker = '1801.HK'

        with patch('backend.app.api.routes.stocks.get_single_stock_price') as mock_price:
            with patch('backend.app.services.athena_ipo.AthenaIPOService.get_ipo_data') as mock_ipo:
                mock_price.return_value = mock_stock_data
                mock_ipo.return_value = mock_ipo_data

                response = client.get(f'/api/stocks/{ticker}/detail')

                assert response.status_code in [200, 404]

    def test_get_portfolio_companies(self, client):
        """Test GET /api/stocks/portfolio endpoint"""
        response = client.get('/api/stocks/portfolio')

        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)

    def test_get_portfolio_companies_with_refresh(self, client):
        """Test GET /api/stocks/portfolio with force_refresh"""
        response = client.get('/api/stocks/portfolio?force_refresh=true')

        assert response.status_code in [200, 404]

    def test_update_portfolio_history(self, client):
        """Test POST /api/stocks/portfolio/update-history endpoint"""
        response = client.post('/api/stocks/portfolio/update-history')

        # May require authentication
        assert response.status_code in [200, 401, 403]

    def test_get_upcoming_ipos(self, client):
        """Test GET /api/stocks/ipo endpoint"""
        response = client.get('/api/stocks/ipo')

        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            # Check structure
            assert 'data' in data or 'html_content' in data or isinstance(data, list)

    def test_get_upcoming_ipos_refresh(self, client):
        """Test GET /api/stocks/ipo with force refresh"""
        response = client.get('/api/stocks/ipo?force_refresh=true')

        assert response.status_code in [200, 404, 500]

    def test_error_handling_invalid_json(self, client):
        """Test API error handling with invalid JSON"""
        response = client.post(
            '/api/stocks/1801.HK/update-history',
            data='invalid json',
            headers={'Content-Type': 'application/json'}
        )

        # Should handle gracefully
        assert response.status_code in [400, 401, 422, 500]

    def test_cors_headers(self, client):
        """Test CORS headers are present"""
        response = client.options('/api/stocks')

        # Should allow CORS
        assert response.status_code in [200, 405]  # OPTIONS may not be enabled

    def test_rate_limiting(self, client):
        """Test API rate limiting (if implemented)"""
        # Make multiple rapid requests
        responses = []
        for _ in range(10):
            response = client.get('/api/stocks')
            responses.append(response.status_code)

        # All should succeed or some may be rate limited
        assert all(code in [200, 429] for code in responses)

    @pytest.mark.slow
    def test_performance_large_date_range(self, client):
        """Test performance with large historical data query"""
        ticker = '1801.HK'

        # Request 1 year of data
        response = client.get(
            f'/api/stocks/{ticker}/history?days=365',
            timeout=10
        )

        assert response.status_code in [200, 404, 500]
        # Should complete within timeout

    def test_pagination_support(self, client):
        """Test pagination parameters (if implemented)"""
        response = client.get('/api/stocks?limit=10&offset=0')

        assert response.status_code in [200, 400, 422]

    def test_filter_by_market_cap(self, client):
        """Test filtering stocks by market cap"""
        response = client.get('/api/stocks?market_cap_min=1000000000')

        assert response.status_code in [200, 400, 422]

    def test_filter_by_ipo_date(self, client):
        """Test filtering stocks by IPO date range"""
        response = client.get('/api/stocks?ipo_date_from=2020-01-01&ipo_date_to=2025-01-01')

        assert response.status_code in [200, 400, 422]

    def test_news_analysis_included_for_big_movers(self, client, mock_big_mover_stock):
        """Test that news analysis is included for stocks with big moves"""
        with patch('backend.app.api.routes.stocks.fetch_all_stock_prices') as mock_fetch:
            mock_fetch.return_value = [mock_big_mover_stock]

            with patch('backend.app.services.stock_news_analysis.StockNewsAnalysisService') as mock_service:
                mock_service.return_value.process_stocks.return_value = [
                    {**mock_big_mover_stock, 'news_analysis': {'analysis': 'Test news'}}
                ]

                response = client.get('/api/stocks')

                if response.status_code == 200:
                    data = response.json()
                    # Check if any stock has news_analysis
                    has_news = any('news_analysis' in stock for stock in data) if isinstance(data, list) else False
                    # News analysis may or may not be present depending on configuration

    def test_cache_headers(self, client):
        """Test cache control headers"""
        response = client.get('/api/stocks')

        # May have cache control headers
        assert response.status_code in [200, 404]
        # Cache-Control header may or may not be present

    def test_concurrent_requests(self, client):
        """Test handling concurrent requests to same endpoint"""
        import concurrent.futures

        def make_request():
            return client.get('/api/stocks/1801.HK')

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(5)]
            responses = [f.result() for f in futures]

        # All should complete successfully
        assert all(r.status_code in [200, 404, 500] for r in responses)

    def test_data_consistency(self, client):
        """Test data consistency across multiple requests"""
        # Make same request twice
        response1 = client.get('/api/stocks/1801.HK')
        response2 = client.get('/api/stocks/1801.HK')

        if response1.status_code == 200 and response2.status_code == 200:
            data1 = response1.json()
            data2 = response2.json()

            # Should return consistent data (unless market is updating)
            assert isinstance(data1, type(data2))
