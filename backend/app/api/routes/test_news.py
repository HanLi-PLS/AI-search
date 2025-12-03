"""
Test endpoint to demonstrate AI news analysis feature with mock big movers
"""
from fastapi import APIRouter
from typing import List, Dict, Any
from datetime import datetime
import asyncio
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/test/big-movers")
async def test_big_movers():
    """
    Test endpoint that returns mock stocks with big moves to demonstrate news analysis
    This shows what the feature looks like when stocks actually move ≥10%
    """

    # Mock stocks with significant moves
    mock_stocks = [
        {
            "ticker": "2561.HK",
            "name": "Visen Pharmaceuticals",
            "current_price": 25.50,
            "open": 22.12,
            "previous_close": 22.12,
            "day_high": 26.00,
            "day_low": 22.00,
            "volume": 8500000,
            "change": 3.38,
            "change_percent": 15.3,
            "intraday_change": 3.38,
            "intraday_change_percent": 15.3,
            "currency": "HKD",
            "last_updated": datetime.now().isoformat(),
            "data_source": "Mock Data (Test)"
        },
        {
            "ticker": "ZBIO",
            "name": "Zenas Biopharma",
            "current_price": 22.45,
            "open": 25.27,
            "previous_close": 25.27,
            "day_high": 25.50,
            "day_low": 22.30,
            "volume": 2100000,
            "change": -2.82,
            "change_percent": -11.2,
            "intraday_change": -2.82,
            "intraday_change_percent": -11.2,
            "currency": "USD",
            "last_updated": datetime.now().isoformat(),
            "data_source": "Mock Data (Test)"
        },
        {
            "ticker": "1801.HK",
            "name": "BeiGene",
            "current_price": 150.00,
            "open": 146.25,
            "previous_close": 146.25,
            "day_high": 151.20,
            "day_low": 145.80,
            "volume": 1200000,
            "change": 3.75,
            "change_percent": 2.5,
            "intraday_change": 3.75,
            "intraday_change_percent": 2.5,
            "currency": "HKD",
            "last_updated": datetime.now().isoformat(),
            "data_source": "Mock Data (Test)"
        }
    ]

    # Add news analysis for big movers
    try:
        from backend.app.services.stock_news_analysis import StockNewsAnalysisService
        news_service = StockNewsAnalysisService()
        mock_stocks = await asyncio.to_thread(news_service.process_stocks, mock_stocks)
        logger.info(f"Processed {len(mock_stocks)} mock stocks for news analysis")
    except Exception as e:
        logger.error(f"Error adding news analysis: {str(e)}")
        # Continue without news analysis if it fails

    return {
        "success": True,
        "message": "Mock data with big movers for testing AI news analysis",
        "note": "2 stocks have ≥10% moves and will show news analysis",
        "stocks": mock_stocks
    }


@router.get("/test/check-news-service")
async def check_news_service():
    """
    Check if the news analysis service is working
    """
    try:
        from backend.app.services.stock_news_analysis import StockNewsAnalysisService

        service = StockNewsAnalysisService()
        stats = service.get_cache_stats()

        return {
            "success": True,
            "service_available": True,
            "cache_stats": stats,
            "message": "News analysis service is working"
        }
    except Exception as e:
        logger.error(f"Error checking news service: {str(e)}")
        return {
            "success": False,
            "service_available": False,
            "error": str(e),
            "message": "News analysis service is not available"
        }
