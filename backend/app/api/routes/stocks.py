"""
Stock tracker API endpoints for HKEX 18A biotech companies
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import yfinance as yf
import pandas as pd
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

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


def get_stock_data(ticker: str) -> Dict[str, Any]:
    """
    Fetch stock data from Yahoo Finance

    Args:
        ticker: Stock ticker symbol (e.g., "1801.HK")

    Returns:
        Dictionary containing stock data
    """
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
            logger.warning(f"No history data available for {ticker}")
            return None

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

        return {
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
        }
    except Exception as e:
        logger.error(f"Error fetching data for {ticker}: {str(e)}", exc_info=True)
        return None


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

    Returns:
        List of stock data for all companies
    """
    results = []

    for company in HKEX_BIOTECH_COMPANIES:
        ticker = company["ticker"]
        name = company["name"]

        logger.info(f"Fetching data for {ticker} - {name}")

        stock_data = get_stock_data(ticker)

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
