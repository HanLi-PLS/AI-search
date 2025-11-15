"""
Finnhub stock data fetching implementation
Add to your existing stocks.py or use as reference
"""
import requests
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def get_stock_data_from_finnhub(ticker: str, api_key: str) -> Optional[Dict[str, Any]]:
    """
    Fetch stock data from Finnhub for HK stocks

    Args:
        ticker: Stock ticker (e.g., "2561.HK")
        api_key: Finnhub API key

    Returns:
        Dictionary containing stock data or None if failed
    """
    try:
        # Finnhub quote endpoint
        url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={api_key}"

        response = requests.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()

        # Finnhub returns: c (current), o (open), h (high), l (low), pc (previous close)
        current_price = float(data.get('c', 0))
        open_price = float(data.get('o', 0))
        high = float(data.get('h', 0))
        low = float(data.get('l', 0))
        previous_close = float(data.get('pc', 0))

        # Calculate change
        change = current_price - previous_close
        change_percent = (change / previous_close * 100) if previous_close != 0 else 0

        # Validate data
        if current_price == 0:
            logger.warning(f"No data found for {ticker} in Finnhub")
            return None

        stock_data = {
            "ticker": ticker,
            "current_price": current_price,
            "open": open_price,
            "previous_close": previous_close,
            "day_high": high,
            "day_low": low,
            "volume": None,  # Not included in basic quote
            "change": change,
            "change_percent": change_percent,
            "market_cap": None,  # Requires separate API call
            "currency": "HKD",
            "last_updated": datetime.now().isoformat(),
            "data_source": "Finnhub"
        }

        return stock_data

    except Exception as e:
        logger.warning(f"Finnhub failed for {ticker}: {str(e)}")
        return None


# Usage in your main stocks.py:
#
# def get_stock_data(ticker: str, code: str = None, name: str = None, use_cache: bool = True):
#     # ... cache check ...
#
#     # 1. Try yfinance
#     # 2. Try Finnhub
#     if FINNHUB_API_KEY:
#         stock_data = get_stock_data_from_finnhub(ticker, FINNHUB_API_KEY)
#         if stock_data:
#             return stock_data
#
#     # 3. Try AKShare
#     # 4. Try GPT-4.1 web search
#     # 5. Demo data
