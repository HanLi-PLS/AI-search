"""
Stock tracker API endpoints for HKEX 18A biotech companies
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import logging
import time
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter()

# Simple in-memory cache with TTL
_stock_cache = {}
_cache_ttl = timedelta(minutes=5)  # Cache for 5 minutes

# Demo/fallback data for when Yahoo Finance is blocked
DEMO_STOCK_DATA = {
    "1801.HK": {"price": 42.50, "change": 1.25, "volume": 12500000, "market_cap": 58000000000},
    "6160.HK": {"price": 125.80, "change": -2.10, "volume": 8900000, "market_cap": 180000000000},
    "9926.HK": {"price": 68.40, "change": 3.50, "volume": 15200000, "market_cap": 95000000000},
    "2696.HK": {"price": 18.75, "change": 0.85, "volume": 6700000, "market_cap": 28000000000},
    "1877.HK": {"price": 32.60, "change": -1.20, "volume": 9800000, "market_cap": 42000000000},
    "6185.HK": {"price": 22.40, "change": 0.60, "volume": 4500000, "market_cap": 18000000000},
    "2269.HK": {"price": 38.90, "change": 1.80, "volume": 22000000, "market_cap": 125000000000},
    "1952.HK": {"price": 15.30, "change": -0.45, "volume": 3200000, "market_cap": 12000000000},
    "2171.HK": {"price": 8.65, "change": 0.35, "volume": 2100000, "market_cap": 6500000000},
    "1996.HK": {"price": 6.82, "change": -0.18, "volume": 1800000, "market_cap": 4200000000},
    "9995.HK": {"price": 28.50, "change": 1.10, "volume": 5600000, "market_cap": 22000000000},
    "9969.HK": {"price": 12.40, "change": -0.30, "volume": 2900000, "market_cap": 8500000000},
    "6996.HK": {"price": 5.45, "change": 0.15, "volume": 1500000, "market_cap": 3800000000},
    "9985.HK": {"price": 3.28, "change": -0.12, "volume": 980000, "market_cap": 2100000000},
    "9688.HK": {"price": 45.60, "change": 2.30, "volume": 7800000, "market_cap": 38000000000},
    "9966.HK": {"price": 9.12, "change": 0.48, "volume": 2400000, "market_cap": 7200000000},
    "9989.HK": {"price": 18.95, "change": -0.65, "volume": 4100000, "market_cap": 16000000000},
    "9982.HK": {"price": 4.67, "change": 0.08, "volume": 1200000, "market_cap": 2800000000},
    "1302.HK": {"price": 1.85, "change": -0.05, "volume": 880000, "market_cap": 1500000000},
}

# HKEX 18A Biotech Companies
HKEX_BIOTECH_COMPANIES = [
    {"ticker": "1801.HK", "name": "Innovent Biologics Inc."},
    {"ticker": "6160.HK", "name": "BeiGene Ltd."},
    {"ticker": "9926.HK", "name": "Akeso Inc."},
    {"ticker": "2696.HK", "name": "Shanghai Henlius Biotech Inc."},
    {"ticker": "1877.HK", "name": "Shanghai Junshi Biosciences"},
    {"ticker": "6185.HK", "name": "CanSino Biologics Inc."},
    {"ticker": "2269.HK", "name": "Wuxi Biologics (Cayman) Inc."},
    {"ticker": "1952.HK", "name": "Everest Medicines Ltd."},
    {"ticker": "2171.HK", "name": "Alphamab Oncology"},
    {"ticker": "1996.HK", "name": "Simcere Pharmaceutical Group Ltd."},
    {"ticker": "9995.HK", "name": "Remegen Co. Ltd."},
    {"ticker": "9969.HK", "name": "Innocare Pharma Ltd."},
    {"ticker": "6996.HK", "name": "Antengene Corporation Ltd."},
    {"ticker": "9985.HK", "name": "Hua Medicine (Shanghai) Ltd."},
    {"ticker": "9688.HK", "name": "Zai Lab Ltd."},
    {"ticker": "9966.HK", "name": "Alphamab Oncology"},
    {"ticker": "9989.HK", "name": "Hutchmed (China) Ltd."},
    {"ticker": "1877.HK", "name": "Shanghai Junshi Biosciences Co. Ltd."},
    {"ticker": "9982.HK", "name": "Sanyou Biopharmaceuticals Co. Ltd."},
    {"ticker": "1302.HK", "name": "Lifetech Scientific Corporation"},
]


def get_stock_data(ticker: str, use_cache: bool = True) -> Dict[str, Any]:
    """
    Fetch stock data from Yahoo Finance with caching and demo data fallback

    Args:
        ticker: Stock ticker symbol (e.g., "1801.HK")
        use_cache: Whether to use cached data

    Returns:
        Dictionary containing stock data
    """
    # Check cache first
    if use_cache and ticker in _stock_cache:
        cached_data, cached_time = _stock_cache[ticker]
        if datetime.now() - cached_time < _cache_ttl:
            logger.info(f"Using cached data for {ticker}")
            return cached_data

    try:
        # Configure yfinance with timeout and user agent
        stock = yf.Ticker(ticker)

        # Try to get info with timeout
        try:
            info = stock.info
        except Exception as e:
            logger.warning(f"Failed to get info for {ticker}: {str(e)}")
            info = {}

        # Get history data - this is more reliable than info
        history = stock.history(period="5d")  # Get 5 days for better reliability

        if history.empty:
            logger.warning(f"No history data available for {ticker}, using demo data")
            # Use demo data as fallback
            return get_demo_stock_data(ticker)

        # Get latest data
        current_price = history['Close'].iloc[-1] if len(history) > 0 else None
        open_price = history['Open'].iloc[-1] if len(history) > 0 else None
        high = history['High'].iloc[-1] if len(history) > 0 else None
        low = history['Low'].iloc[-1] if len(history) > 0 else None
        volume = history['Volume'].iloc[-1] if len(history) > 0 else None

        # Get previous close (from previous day if available)
        if len(history) >= 2:
            previous_close = history['Close'].iloc[-2]
        else:
            previous_close = info.get('previousClose', current_price)

        # Calculate changes
        if current_price and previous_close and previous_close != 0:
            change = current_price - previous_close
            change_percent = (change / previous_close * 100)
        else:
            change = 0
            change_percent = 0

        stock_data = {
            "ticker": ticker,
            "current_price": float(current_price) if current_price else None,
            "open": float(open_price) if open_price else None,
            "previous_close": float(previous_close) if previous_close else None,
            "day_high": float(high) if high else None,
            "day_low": float(low) if low else None,
            "volume": int(volume) if volume and not pd.isna(volume) else None,
            "change": float(change),
            "change_percent": float(change_percent),
            "market_cap": info.get('marketCap'),
            "currency": info.get('currency', 'HKD'),
            "last_updated": datetime.now().isoformat(),
            "data_source": "Yahoo Finance"
        }

        # Cache the result
        _stock_cache[ticker] = (stock_data, datetime.now())
        return stock_data

    except Exception as e:
        logger.error(f"Error fetching data for {ticker}: {str(e)}, using demo data")
        # Use demo data as fallback
        return get_demo_stock_data(ticker)


def get_demo_stock_data(ticker: str) -> Dict[str, Any]:
    """
    Get demo/fallback stock data when Yahoo Finance fails

    Args:
        ticker: Stock ticker symbol

    Returns:
        Dictionary containing demo stock data
    """
    if ticker not in DEMO_STOCK_DATA:
        return None

    demo = DEMO_STOCK_DATA[ticker]
    current_price = demo["price"]
    change = demo["change"]
    change_percent = (change / current_price) * 100
    previous_close = current_price - change

    stock_data = {
        "ticker": ticker,
        "current_price": current_price,
        "open": current_price - 0.5,
        "previous_close": previous_close,
        "day_high": current_price + abs(change) * 0.8,
        "day_low": current_price - abs(change) * 0.6,
        "volume": demo["volume"],
        "change": change,
        "change_percent": change_percent,
        "market_cap": demo["market_cap"],
        "currency": "HKD",
        "last_updated": datetime.now().isoformat(),
        "data_source": "Demo Data (Yahoo Finance unavailable)"
    }

    # Cache demo data too
    _stock_cache[ticker] = (stock_data, datetime.now())
    return stock_data


@router.get("/stocks/companies")
async def get_companies():
    """
    Get list of all HKEX 18A biotech companies

    Returns:
        List of companies with ticker and name
    """
    return {"companies": HKEX_BIOTECH_COMPANIES}


@router.get("/stocks/prices")
async def get_all_prices():
    """
    Get current prices for all HKEX 18A biotech companies
    Uses caching and rate limiting to avoid Yahoo Finance 429 errors

    Returns:
        List of stock data for all companies
    """
    results = []

    for i, company in enumerate(HKEX_BIOTECH_COMPANIES):
        ticker = company["ticker"]
        name = company["name"]

        logger.info(f"Fetching data for {ticker} - {name}")

        stock_data = get_stock_data(ticker, use_cache=True)

        if stock_data:
            stock_data["name"] = name
            results.append(stock_data)
        else:
            # Return company info with error
            results.append({
                "ticker": ticker,
                "name": name,
                "error": "Unable to fetch data",
                "current_price": None,
                "change": None,
                "change_percent": None,
                "last_updated": datetime.now().isoformat(),
            })

        # Add delay between requests to avoid rate limiting (except for last item)
        if i < len(HKEX_BIOTECH_COMPANIES) - 1:
            await asyncio.sleep(0.5)  # 500ms delay between requests

    return results


@router.get("/stocks/price/{ticker}")
async def get_price(ticker: str):
    """
    Get current price for a specific ticker

    Args:
        ticker: Stock ticker symbol (e.g., "1801.HK")

    Returns:
        Stock data for the specified ticker
    """
    # Find company name
    company = next((c for c in HKEX_BIOTECH_COMPANIES if c["ticker"] == ticker), None)

    if not company:
        raise HTTPException(status_code=404, detail=f"Ticker {ticker} not found")

    stock_data = get_stock_data(ticker)

    if not stock_data:
        raise HTTPException(status_code=500, detail=f"Unable to fetch data for {ticker}")

    stock_data["name"] = company["name"]
    return stock_data


@router.get("/stocks/history/{ticker}")
async def get_history(ticker: str, period: str = "1mo"):
    """
    Get historical data for a specific ticker

    Args:
        ticker: Stock ticker symbol (e.g., "1801.HK")
        period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)

    Returns:
        Historical stock data
    """
    valid_periods = ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"]

    if period not in valid_periods:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid period. Must be one of: {', '.join(valid_periods)}"
        )

    try:
        stock = yf.Ticker(ticker)
        history = stock.history(period=period)

        if history.empty:
            raise HTTPException(status_code=404, detail=f"No historical data found for {ticker}")

        # Convert to list of dictionaries
        data = []
        for date, row in history.iterrows():
            data.append({
                "date": date.isoformat(),
                "open": float(row['Open']),
                "high": float(row['High']),
                "low": float(row['Low']),
                "close": float(row['Close']),
                "volume": int(row['Volume']),
            })

        return {
            "ticker": ticker,
            "period": period,
            "data": data
        }

    except Exception as e:
        logger.error(f"Error fetching historical data for {ticker}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stocks/upcoming-ipos")
async def get_upcoming_ipos():
    """
    Get upcoming HKEX biotech IPOs (placeholder)

    Returns:
        List of upcoming IPOs
    """
    # This is a placeholder - real implementation would need HKEX API or web scraping
    return {
        "message": "IPO data is not available yet",
        "upcoming_ipos": []
    }
