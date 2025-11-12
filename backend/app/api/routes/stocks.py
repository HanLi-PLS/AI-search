"""
Stock tracker API endpoints for HKEX 18A biotech companies
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
import pandas as pd
from datetime import datetime, timedelta
import logging
import asyncio
import requests
from bs4 import BeautifulSoup
import re

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    logging.warning("AKShare not available, will use demo data")

logger = logging.getLogger(__name__)

router = APIRouter()

# Simple in-memory cache with TTL
_stock_cache = {}
_cache_ttl = timedelta(minutes=5)  # Cache for 5 minutes

# Company list cache (24 hour TTL)
_company_list_cache = None
_company_list_cache_time = None
_company_list_cache_ttl = timedelta(hours=24)

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

# HKEX 18A Biotech Companies - Fallback list if web scraping fails
FALLBACK_HKEX_BIOTECH_COMPANIES = [
    {"ticker": "1801.HK", "code": "01801", "name": "Innovent Biologics Inc."},
    {"ticker": "6160.HK", "code": "06160", "name": "BeiGene Ltd."},
    {"ticker": "9926.HK", "code": "09926", "name": "Akeso Inc."},
    {"ticker": "2696.HK", "code": "02696", "name": "Shanghai Henlius Biotech Inc."},
    {"ticker": "1877.HK", "code": "01877", "name": "Shanghai Junshi Biosciences"},
    {"ticker": "6185.HK", "code": "06185", "name": "CanSino Biologics Inc."},
    {"ticker": "2269.HK", "code": "02269", "name": "Wuxi Biologics (Cayman) Inc."},
    {"ticker": "1952.HK", "code": "01952", "name": "Everest Medicines Ltd."},
    {"ticker": "2171.HK", "code": "02171", "name": "Alphamab Oncology"},
    {"ticker": "1996.HK", "code": "01996", "name": "Simcere Pharmaceutical Group Ltd."},
    {"ticker": "9995.HK", "code": "09995", "name": "Remegen Co. Ltd."},
    {"ticker": "9969.HK", "code": "09969", "name": "Innocare Pharma Ltd."},
    {"ticker": "6996.HK", "code": "06996", "name": "Antengene Corporation Ltd."},
    {"ticker": "9985.HK", "code": "09985", "name": "Hua Medicine (Shanghai) Ltd."},
    {"ticker": "9688.HK", "code": "09688", "name": "Zai Lab Ltd."},
    {"ticker": "9966.HK", "code": "09966", "name": "Alphamab Oncology"},
    {"ticker": "9989.HK", "code": "09989", "name": "Hutchmed (China) Ltd."},
    {"ticker": "9982.HK", "code": "09982", "name": "Sanyou Biopharmaceuticals Co. Ltd."},
    {"ticker": "1302.HK", "code": "01302", "name": "Lifetech Scientific Corporation"},
]


def scrape_hkex_biotech_companies() -> Optional[List[Dict[str, str]]]:
    """
    Scrape HKEX biotech company list from AAStocks website

    Returns:
        List of companies with ticker, code, and name, or None if scraping fails
    """
    try:
        url = "https://www.aastocks.com/sc/stocks/market/topic/biotech?t=1"

        # Use headers to avoid 403 Forbidden
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Referer': 'https://www.aastocks.com/',
        }

        logger.info(f"Scraping biotech companies from {url}")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        companies = []

        # Find the table with stock data
        # AAStocks typically uses tables for stock listings
        tables = soup.find_all('table')

        for table in tables:
            rows = table.find_all('tr')

            for row in rows:
                cells = row.find_all(['td', 'th'])

                # Look for cells containing stock codes (format: 01801, 06160, etc.)
                for i, cell in enumerate(cells):
                    text = cell.get_text(strip=True)

                    # Match HK stock code pattern (5 digits, possibly with leading zero)
                    code_match = re.match(r'^(\d{5})$', text)

                    if code_match:
                        code = code_match.group(1)

                        # Get company name from adjacent cell
                        name = None
                        if i + 1 < len(cells):
                            name = cells[i + 1].get_text(strip=True)

                        if name:
                            # Convert code to ticker format (e.g., "01801" -> "1801.HK")
                            ticker_num = str(int(code))  # Remove leading zeros
                            ticker = f"{ticker_num}.HK"

                            companies.append({
                                "ticker": ticker,
                                "code": code,
                                "name": name
                            })

        if companies:
            logger.info(f"Successfully scraped {len(companies)} biotech companies from AAStocks")
            return companies
        else:
            logger.warning("No companies found in scraped data")
            return None

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching AAStocks page: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error parsing AAStocks data: {str(e)}")
        return None


def get_hkex_biotech_companies() -> List[Dict[str, str]]:
    """
    Get HKEX biotech company list, using cache or scraping from AAStocks
    Falls back to hardcoded list if scraping fails

    Returns:
        List of companies with ticker, code, and name
    """
    global _company_list_cache, _company_list_cache_time

    # Check if cache is valid
    if _company_list_cache is not None and _company_list_cache_time is not None:
        cache_age = datetime.now() - _company_list_cache_time
        if cache_age < _company_list_cache_ttl:
            logger.debug(f"Using cached company list (age: {cache_age})")
            return _company_list_cache

    # Try to scrape fresh data
    logger.info("Company list cache expired or empty, scraping fresh data")
    scraped_companies = scrape_hkex_biotech_companies()

    if scraped_companies:
        # Update cache
        _company_list_cache = scraped_companies
        _company_list_cache_time = datetime.now()
        return scraped_companies
    else:
        # Fall back to hardcoded list
        logger.warning("Scraping failed, using fallback company list")
        _company_list_cache = FALLBACK_HKEX_BIOTECH_COMPANIES
        _company_list_cache_time = datetime.now()
        return FALLBACK_HKEX_BIOTECH_COMPANIES


def get_stock_data_from_akshare(code: str, ticker: str) -> Dict[str, Any]:
    """
    Fetch stock data from AKShare for a specific HK stock

    Args:
        code: HK stock code in 5-digit format (e.g., "01801")
        ticker: Stock ticker (e.g., "1801.HK")

    Returns:
        Dictionary containing stock data
    """
    try:
        # Fetch all HK stocks data
        df = ak.stock_hk_spot_em()

        # Filter for our specific stock
        stock_row = df[df['代码'] == code]

        if stock_row.empty:
            logger.warning(f"No data found for {code} in AKShare")
            return None

        row = stock_row.iloc[0]

        # Extract data (column names in Chinese)
        current_price = float(row.get('最新价', 0))
        previous_close = float(row.get('昨收', current_price))
        open_price = float(row.get('今开', current_price))
        high = float(row.get('最高', current_price))
        low = float(row.get('最低', current_price))
        volume = int(row.get('成交量', 0))
        turnover = float(row.get('成交额', 0))
        change = float(row.get('涨跌额', 0))
        change_percent = float(row.get('涨跌幅', 0))

        stock_data = {
            "ticker": ticker,
            "current_price": current_price,
            "open": open_price,
            "previous_close": previous_close,
            "day_high": high,
            "day_low": low,
            "volume": volume,
            "turnover": turnover,
            "change": change,
            "change_percent": change_percent,
            "market_cap": None,  # AKShare doesn't provide market cap in spot data
            "currency": "HKD",
            "last_updated": datetime.now().isoformat(),
            "data_source": "AKShare (East Money)"
        }

        return stock_data

    except Exception as e:
        logger.error(f"Error fetching AKShare data for {code}: {str(e)}")
        return None


def get_stock_data(ticker: str, code: str = None, use_cache: bool = True) -> Dict[str, Any]:
    """
    Fetch stock data with caching, tries AKShare first, then falls back to demo data

    Args:
        ticker: Stock ticker symbol (e.g., "1801.HK")
        code: HK stock code in 5-digit format (e.g., "01801")
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

    # Try AKShare first if available
    if AKSHARE_AVAILABLE and code:
        logger.info(f"Fetching {ticker} from AKShare")
        stock_data = get_stock_data_from_akshare(code, ticker)

        if stock_data:
            # Cache the result
            _stock_cache[ticker] = (stock_data, datetime.now())
            return stock_data

    # Fall back to demo data
    logger.warning(f"Using demo data for {ticker}")
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
    companies = get_hkex_biotech_companies()
    return {"companies": companies}


@router.get("/stocks/prices")
async def get_all_prices():
    """
    Get current prices for all HKEX 18A biotech companies
    Uses caching and rate limiting to avoid Yahoo Finance 429 errors

    Returns:
        List of stock data for all companies
    """
    results = []
    companies = get_hkex_biotech_companies()

    for i, company in enumerate(companies):
        ticker = company["ticker"]
        code = company.get("code")  # Get the 5-digit code for AKShare
        name = company["name"]

        logger.info(f"Fetching data for {ticker} ({code}) - {name}")

        stock_data = get_stock_data(ticker, code=code, use_cache=True)

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
        if i < len(companies) - 1:
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
    # Find company info
    companies = get_hkex_biotech_companies()
    company = next((c for c in companies if c["ticker"] == ticker), None)

    if not company:
        raise HTTPException(status_code=404, detail=f"Ticker {ticker} not found")

    stock_data = get_stock_data(ticker, code=company.get("code"))

    if not stock_data:
        raise HTTPException(status_code=500, detail=f"Unable to fetch data for {ticker}")

    stock_data["name"] = company["name"]
    return stock_data


@router.get("/stocks/history/{ticker}")
async def get_history(ticker: str, period: str = "1mo"):
    """
    Get historical data for a specific ticker

    Note: Historical data functionality is currently being migrated to AKShare.
    This endpoint will return historical data in a future update.

    Args:
        ticker: Stock ticker symbol (e.g., "1801.HK")
        period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)

    Returns:
        Historical stock data (placeholder for now)
    """
    return {
        "ticker": ticker,
        "period": period,
        "message": "Historical data feature coming soon with AKShare integration",
        "data": []
    }


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
