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
import os
from backend.app.config import settings

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    logging.warning("AKShare not available")

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = False  # Disabled - doesn't work for HK stocks
except ImportError:
    YFINANCE_AVAILABLE = False

# Finnhub API key from settings (loaded from AWS Secrets Manager or environment)
FINNHUB_API_KEY = settings.FINNHUB_API_KEY
FINNHUB_AVAILABLE = FINNHUB_API_KEY is not None and FINNHUB_API_KEY != ""

# Tushare API token from settings (loaded from AWS Secrets Manager or environment)
TUSHARE_API_TOKEN = settings.TUSHARE_API_TOKEN
TUSHARE_AVAILABLE = False
if TUSHARE_API_TOKEN:
    try:
        import tushare as ts
        ts.set_token(TUSHARE_API_TOKEN)
        TUSHARE_AVAILABLE = True
    except ImportError:
        logging.warning("Tushare not available - install with: pip install tushare")
    except Exception as e:
        logging.warning(f"Tushare initialization failed: {str(e)}")

logger = logging.getLogger(__name__)

router = APIRouter()

# Simple in-memory cache with TTL
_stock_cache = {}
_cache_ttl = timedelta(hours=12)  # Cache for 12 hours (refreshed at 12 AM and 12 PM)

# Company list cache (24 hour TTL)
_company_list_cache = None
_company_list_cache_time = None
_company_list_cache_ttl = timedelta(hours=24)

# No demo/fallback data - return None if real sources fail

# HKEX 18A Biotech Companies - Fallback list if web scraping fails
# Updated from AAStocks biotech page as of 2025-11-12 (66 companies total)
FALLBACK_HKEX_BIOTECH_COMPANIES = [
    {"ticker": "2561.HK", "code": "02561", "name": "维升药业－Ｂ"},
    {"ticker": "2552.HK", "code": "02552", "name": "华领医药－Ｂ"},
    {"ticker": "2630.HK", "code": "02630", "name": "旺山旺水－Ｂ"},
    {"ticker": "2315.HK", "code": "02315", "name": "百奥赛图－Ｂ"},
    {"ticker": "6996.HK", "code": "06996", "name": "德琪医药－Ｂ"},
    {"ticker": "1541.HK", "code": "01541", "name": "宜明昂科－Ｂ"},
    {"ticker": "9877.HK", "code": "09877", "name": "健世科技－Ｂ"},
    {"ticker": "2197.HK", "code": "02197", "name": "三叶草生物－Ｂ"},
    {"ticker": "2160.HK", "code": "02160", "name": "心通医疗－Ｂ"},
    {"ticker": "2487.HK", "code": "02487", "name": "科笛－Ｂ"},
    {"ticker": "3681.HK", "code": "03681", "name": "中国抗体－Ｂ"},
    {"ticker": "2181.HK", "code": "02181", "name": "迈博药业－Ｂ"},
    {"ticker": "6978.HK", "code": "06978", "name": "永泰生物－Ｂ"},
    {"ticker": "6622.HK", "code": "06622", "name": "兆科眼科－Ｂ"},
    {"ticker": "2179.HK", "code": "02179", "name": "瑞科生物－Ｂ"},
    {"ticker": "2511.HK", "code": "02511", "name": "君圣泰医药－Ｂ"},
    {"ticker": "2185.HK", "code": "02185", "name": "百心安－Ｂ"},
    {"ticker": "6998.HK", "code": "06998", "name": "嘉和生物－Ｂ"},
    {"ticker": "1875.HK", "code": "01875", "name": "东曜药业－Ｂ"},
    {"ticker": "6609.HK", "code": "06609", "name": "心玮医疗－Ｂ"},
    {"ticker": "2126.HK", "code": "02126", "name": "药明巨诺－Ｂ"},
    {"ticker": "2216.HK", "code": "02216", "name": "堃博医疗－Ｂ"},
    {"ticker": "2137.HK", "code": "02137", "name": "腾盛博药－Ｂ"},
    {"ticker": "6628.HK", "code": "06628", "name": "创胜集团－Ｂ"},
    {"ticker": "2251.HK", "code": "02251", "name": "鹰瞳科技－Ｂ"},
    {"ticker": "2898.HK", "code": "02898", "name": "盛禾生物－Ｂ"},
    {"ticker": "2235.HK", "code": "02235", "name": "微泰医疗－Ｂ"},
    {"ticker": "2500.HK", "code": "02500", "name": "启明医疗－Ｂ"},
    {"ticker": "6922.HK", "code": "06922", "name": "康沣生物－Ｂ"},
    {"ticker": "1228.HK", "code": "01228", "name": "北海康成－Ｂ"},
    {"ticker": "9939.HK", "code": "09939", "name": "开拓药业－Ｂ"},
    {"ticker": "2257.HK", "code": "02257", "name": "圣诺医药－Ｂ"},
    {"ticker": "2496.HK", "code": "02496", "name": "友芝友生物－Ｂ"},
    {"ticker": "2563.HK", "code": "02563", "name": "华昊中天医药－Ｂ"},
    {"ticker": "2297.HK", "code": "02297", "name": "润迈德－Ｂ"},
    {"ticker": "2170.HK", "code": "02170", "name": "贝康医疗－Ｂ"},
    {"ticker": "6990.HK", "code": "06990", "name": "科伦博泰生物－Ｂ"},
    {"ticker": "2617.HK", "code": "02617", "name": "药捷安康－Ｂ"},
    {"ticker": "9606.HK", "code": "09606", "name": "映恩生物－Ｂ"},
    {"ticker": "2252.HK", "code": "02252", "name": "微创机器人－Ｂ"},
    {"ticker": "6855.HK", "code": "06855", "name": "亚盛医药－Ｂ"},
    {"ticker": "2162.HK", "code": "02162", "name": "康诺亚－Ｂ"},
    {"ticker": "2629.HK", "code": "02629", "name": "MIRXES-B"},
    {"ticker": "2565.HK", "code": "02565", "name": "派格生物医药－Ｂ"},
    {"ticker": "2591.HK", "code": "02591", "name": "银诺医药－Ｂ"},
    {"ticker": "2627.HK", "code": "02627", "name": "中慧生物－Ｂ"},
    {"ticker": "2142.HK", "code": "02142", "name": "和铂医药－Ｂ"},
    {"ticker": "2157.HK", "code": "02157", "name": "乐普生物－Ｂ"},
    {"ticker": "1672.HK", "code": "01672", "name": "歌礼制药－Ｂ"},
    {"ticker": "2575.HK", "code": "02575", "name": "轩竹生物－Ｂ"},
    {"ticker": "2595.HK", "code": "02595", "name": "劲方医药－Ｂ"},
    {"ticker": "2171.HK", "code": "02171", "name": "科济药业－Ｂ"},
    {"ticker": "9966.HK", "code": "09966", "name": "康宁杰瑞制药－Ｂ"},
    {"ticker": "2256.HK", "code": "02256", "name": "和誉－Ｂ"},
    {"ticker": "9887.HK", "code": "09887", "name": "维立志博－Ｂ"},
    {"ticker": "6681.HK", "code": "06681", "name": "脑动极光－Ｂ"},
    {"ticker": "2616.HK", "code": "02616", "name": "基石药业－Ｂ"},
    {"ticker": "1477.HK", "code": "01477", "name": "欧康维视生物－Ｂ"},
    {"ticker": "1167.HK", "code": "01167", "name": "加科思－Ｂ"},
    {"ticker": "2105.HK", "code": "02105", "name": "来凯医药－Ｂ"},
    {"ticker": "2410.HK", "code": "02410", "name": "同源康医药－Ｂ"},
    {"ticker": "2509.HK", "code": "02509", "name": "荃信生物－Ｂ"},
    {"ticker": "2480.HK", "code": "02480", "name": "绿竹生物－Ｂ"},
    {"ticker": "9996.HK", "code": "09996", "name": "沛嘉医疗－Ｂ"},
    {"ticker": "6669.HK", "code": "06669", "name": "先瑞达医疗－Ｂ"},
    {"ticker": "2592.HK", "code": "02592", "name": "拨康视云－Ｂ"},
]


def scrape_hkex_biotech_companies() -> Optional[List[Dict[str, str]]]:
    """
    Scrape HKEX biotech company list from AAStocks website

    Returns:
        List of companies with ticker, code, and name, or None if scraping fails
    """
    try:
        # Try both Traditional Chinese and Simplified Chinese versions
        urls = [
            "https://www.aastocks.com/tc/stocks/market/topic/biotech",
            "https://www.aastocks.com/sc/stocks/market/topic/biotech?t=1"
        ]

        # Use headers to avoid 403 Forbidden
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Referer': 'https://www.aastocks.com/',
        }

        companies = []

        for url in urls:
            try:
                logger.info(f"Scraping biotech companies from {url}")
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()

                soup = BeautifulSoup(response.content, 'html.parser')
                page_text = str(soup)

                # Method 1: Parse JavaScript tsData array (contains ALL companies)
                # Pattern: var tsData = [{d0:"...symbol=XXXXX...>XXXXX.HK</a>...<span style='line-height:17px'>Name</span>..."}]
                tsdata_pattern = r"symbol=(\d{5})[^>]+>(\d+\.HK)</a>.*?<span style=['\"]line-height:17px['\"]>([^<]+)</span>"
                js_matches = re.findall(tsdata_pattern, page_text, re.DOTALL)

                for code, ticker, name in js_matches:
                    name = name.strip()
                    # Avoid duplicates
                    if not any(c['code'] == code for c in companies):
                        companies.append({
                            "ticker": ticker,
                            "code": code,
                            "name": name
                        })

                # Method 2: Parse HTML table (backup method)
                if not companies:
                    # AAStocks structure: <a href='/tc/stocks/quote/detail-quote.aspx?symbol=06990'>06990.HK</a>
                    # Company name in: <span style='line-height:17px'>company name</span>
                    stock_links = soup.find_all('a', href=re.compile(r'/stocks/quote/detail-quote\.aspx\?symbol=\d{5}'))

                    for link in stock_links:
                        # Extract ticker from link text (e.g., "06990.HK")
                        ticker = link.get_text(strip=True)

                        if ticker and '.HK' in ticker:
                            # Extract 5-digit code
                            code = ticker.replace('.HK', '').zfill(5)

                            # Find company name in the same row
                            row = link.find_parent('tr')
                            if row:
                                # Look for company name in span with line-height style
                                name_span = row.find('span', style=re.compile(r'line-height'))
                                if name_span:
                                    name = name_span.get_text(strip=True)

                                    # Avoid duplicates
                                    if not any(c['code'] == code for c in companies):
                                        companies.append({
                                            "ticker": ticker,
                                            "code": code,
                                            "name": name
                                        })

                if companies:
                    logger.info(f"Scraped {len(companies)} companies from {url}")
                    # Don't return yet - try other URLs to get more companies

            except requests.exceptions.RequestException as e:
                logger.debug(f"Failed to fetch {url}: {str(e)}")
                continue  # Try next URL

        if not companies:
            logger.warning("No companies found in scraped data from any URL")
            return None

        logger.info(f"Successfully scraped {len(companies)} biotech companies from AAStocks")
        return companies

    except Exception as e:
        logger.error(f"Error parsing AAStocks data: {str(e)}")
        return None


def get_hkex_biotech_companies() -> List[Dict[str, str]]:
    """
    Get HKEX biotech company list from verified fallback list

    Note: Web scraping from AAStocks was unreliable (ticker/name mismatches),
    so we use a curated list that's manually verified and updated.

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

    # Use the verified fallback list (web scraping was unreliable)
    logger.info("Loading HKEX 18A biotech company list from verified source")
    _company_list_cache = FALLBACK_HKEX_BIOTECH_COMPANIES
    _company_list_cache_time = datetime.now()
    return FALLBACK_HKEX_BIOTECH_COMPANIES


def get_stock_data_from_yfinance(ticker: str) -> Dict[str, Any]:
    """
    Fetch stock data from yfinance for a specific HK stock

    Args:
        ticker: Stock ticker (e.g., "1801.HK")

    Returns:
        Dictionary containing stock data or None if failed
    """
    try:
        import time

        stock = yf.Ticker(ticker)

        # Add a small delay to avoid rate limiting
        time.sleep(0.1)

        # Get current data
        info = stock.info
        hist = stock.history(period="2d")  # Get last 2 days for previous close

        if hist.empty or len(hist) == 0:
            logger.warning(f"No historical data found for {ticker} in yfinance")
            return None

        latest = hist.iloc[-1]
        current_price = float(latest['Close'])
        open_price = float(latest['Open'])
        high = float(latest['High'])
        low = float(latest['Low'])
        volume = int(latest['Volume'])

        # Calculate previous close and change
        if len(hist) > 1:
            previous_close = float(hist.iloc[-2]['Close'])
        else:
            previous_close = current_price

        change = current_price - previous_close
        change_percent = (change / previous_close * 100) if previous_close != 0 else 0

        # Try to get market cap from info
        market_cap = info.get('marketCap', None)

        stock_data = {
            "ticker": ticker,
            "current_price": current_price,
            "open": open_price,
            "previous_close": previous_close,
            "day_high": high,
            "day_low": low,
            "volume": volume,
            "change": change,
            "change_percent": change_percent,
            "market_cap": market_cap,
            "currency": "HKD",
            "last_updated": datetime.now().isoformat(),
            "data_source": "Yahoo Finance (yfinance)"
        }

        return stock_data

    except Exception as e:
        logger.debug(f"Error fetching yfinance data for {ticker}: {str(e)}")
        return None


def get_stock_data_from_finnhub(ticker: str) -> Dict[str, Any]:
    """
    Fetch stock data from Finnhub for a specific HK stock

    Args:
        ticker: Stock ticker (e.g., "1801.HK")

    Returns:
        Dictionary containing stock data or None if failed
    """
    try:
        # Finnhub quote endpoint
        url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_API_KEY}"

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
        logger.debug(f"Error fetching Finnhub data for {ticker}: {str(e)}")
        return None


def get_stock_data_from_tushare(ticker: str, code: str = None, get_name: bool = True) -> Dict[str, Any]:
    """
    Fetch stock data from Tushare Pro for Hong Kong stocks

    Args:
        ticker: Stock ticker (e.g., "1801.HK")
        code: HK stock code in 5-digit format (e.g., "01801")
        get_name: Whether to try fetching company name from Tushare

    Returns:
        Dictionary containing stock data or None if failed
    """
    if not TUSHARE_AVAILABLE:
        return None

    try:
        import tushare as ts

        # Initialize Pro API
        pro = ts.pro_api()

        # Convert ticker to Tushare format (needs 5-digit code with leading zeros)
        # e.g., "1801.HK" -> "01801.HK"
        if code:
            # Use the provided 5-digit code
            tushare_ticker = f"{code}.HK"
        else:
            # Extract code from ticker and pad to 5 digits
            stock_code = ticker.split('.')[0]
            tushare_ticker = f"{stock_code.zfill(5)}.HK"

        logger.debug(f"Using Tushare ticker format: {tushare_ticker}")

        # Try to get company name from Tushare hk_basic (if user has access)
        company_name = None
        if get_name:
            try:
                basic_df = pro.hk_basic(ts_code=tushare_ticker, fields='ts_code,name')
                if basic_df is not None and not basic_df.empty:
                    company_name = basic_df.iloc[0]['name']
                    logger.debug(f"Got company name from Tushare: {company_name}")
            except Exception as e:
                logger.debug(f"Cannot fetch name from hk_basic for {tushare_ticker}: {str(e)}")
                # Will use name from AAStocks instead

        # Fetch latest daily data (most recent trading day)
        # Tushare uses format like "01801.HK"
        df = pro.hk_daily(ts_code=tushare_ticker)

        if df is None or df.empty:
            logger.warning(f"No data found for {ticker} in Tushare")
            return None

        # Get the most recent trading day
        latest = df.iloc[0]

        # Extract data
        current_price = float(latest['close'])
        previous_close = float(latest['pre_close'])
        open_price = float(latest['open'])
        high = float(latest['high'])
        low = float(latest['low'])
        volume = int(latest['vol']) if latest['vol'] else None
        change = float(latest['change']) if 'change' in latest else (current_price - previous_close)
        change_percent = float(latest['pct_chg']) if 'pct_chg' in latest else (change / previous_close * 100 if previous_close != 0 else 0)

        stock_data = {
            "ticker": ticker,
            "current_price": current_price,
            "open": open_price,
            "previous_close": previous_close,
            "day_high": high,
            "day_low": low,
            "volume": volume,
            "change": change,
            "change_percent": change_percent,
            "market_cap": None,  # Tushare doesn't provide market cap in daily data
            "currency": "HKD",
            "last_updated": datetime.now().isoformat(),
            "data_source": "Tushare Pro"
        }

        # Add company name if we got it from Tushare
        if company_name:
            stock_data["name"] = company_name

        return stock_data

    except Exception as e:
        logger.debug(f"Error fetching Tushare data for {ticker}: {str(e)}")
        return None


def get_stock_data_from_websearch(ticker: str, name: str = None) -> Dict[str, Any]:
    """
    Fetch stock data using GPT-4 with web search tool as fallback when APIs fail

    Args:
        ticker: Stock ticker (e.g., "1801.HK")
        name: Company name for better search results (optional)

    Returns:
        Dictionary containing stock data or None if failed
    """
    try:
        from openai import OpenAI
        import json

        client = OpenAI(api_key=settings.get_openai_api_key())

        # Construct search query
        company_info = f"{name} " if name else ""
        search_query = f"{company_info}{ticker} HKEX Hong Kong stock current price today"

        logger.debug(f"Searching web for {ticker} stock price: {search_query}")

        # Use GPT-4.1 with built-in web search capability
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {
                    "role": "system",
                    "content": """You are a financial data assistant. Search the web and extract stock price information.
Return ONLY a valid JSON object with these exact fields:
- current_price (number): Current stock price in HKD
- change (number): Price change from previous close in HKD
- change_percent (number): Percentage change
- volume (number or null): Trading volume
- previous_close (number): Previous closing price in HKD

If you cannot find reliable data, return null. Do not include explanations, only the JSON."""
                },
                {
                    "role": "user",
                    "content": f"Search the web for current stock price of {ticker} ({company_info}HKEX biotech company). Find data from HKEX, AAStocks, or financial news sites. Return the data as JSON."
                }
            ],
            max_tokens=300,
            temperature=0
        )

        result_text = response.choices[0].message.content.strip()

        # Parse the JSON response
        try:
            # Remove markdown code blocks if present
            if '```' in result_text:
                # Extract JSON from code block
                if '```json' in result_text:
                    result_text = result_text.split('```json')[1].split('```')[0]
                else:
                    result_text = result_text.split('```')[1].split('```')[0]
                result_text = result_text.strip()

            data = json.loads(result_text)

            if data is None or not isinstance(data, dict):
                logger.warning(f"Web search returned no data for {ticker}")
                return None

            # Validate we have at least a current price
            current_price = data.get('current_price')
            if current_price is None or current_price <= 0:
                logger.warning(f"Invalid price from web search for {ticker}: {current_price}")
                return None

            # Calculate previous_close and change if not provided
            change = data.get('change', 0)
            change_percent = data.get('change_percent', 0)
            previous_close = data.get('previous_close')

            if previous_close is None and change != 0:
                previous_close = current_price - change
            elif previous_close is None:
                previous_close = current_price

            stock_data = {
                "ticker": ticker,
                "current_price": float(current_price),
                "open": float(current_price),  # Approximate
                "previous_close": float(previous_close),
                "day_high": float(current_price * 1.02),  # Approximate
                "day_low": float(current_price * 0.98),   # Approximate
                "volume": int(data.get('volume', 0)) if data.get('volume') else None,
                "change": float(change),
                "change_percent": float(change_percent),
                "market_cap": None,
                "currency": "HKD",
                "last_updated": datetime.now().isoformat(),
                "data_source": "Web Search (GPT-4.1)"
            }

            logger.info(f"✓ Got real data from web search for {ticker}: HKD {current_price}")
            return stock_data

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse web search result for {ticker}: {result_text[:100]}")
            return None

    except Exception as e:
        logger.warning(f"Web search failed for {ticker}: {str(e)}")
        return None


def get_stock_data_from_akshare(code: str, ticker: str, retry_count: int = 2) -> Dict[str, Any]:
    """
    Fetch stock data from AKShare for a specific HK stock with retry logic

    Args:
        code: HK stock code in 5-digit format (e.g., "01801")
        ticker: Stock ticker (e.g., "1801.HK")
        retry_count: Number of retries on failure

    Returns:
        Dictionary containing stock data or None if failed
    """
    import time

    for attempt in range(retry_count + 1):
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
            if attempt < retry_count:
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s
                logger.debug(f"AKShare attempt {attempt + 1} failed for {code}, retrying in {wait_time}s: {str(e)}")
                time.sleep(wait_time)
            else:
                logger.debug(f"AKShare failed for {code} after {retry_count + 1} attempts: {str(e)}")
                return None

    return None


def get_stock_data(ticker: str, code: str = None, name: str = None, use_cache: bool = True) -> Optional[Dict[str, Any]]:
    """
    Fetch stock data with caching, tries multiple sources: Tushare -> Finnhub -> AKShare -> Web Search (GPT-4.1)

    Args:
        ticker: Stock ticker symbol (e.g., "1801.HK")
        code: HK stock code in 5-digit format (e.g., "01801")
        name: Company name for web search (optional)
        use_cache: Whether to use cached data

    Returns:
        Dictionary containing stock data, or None if all sources fail
    """
    # Check cache first
    if use_cache and ticker in _stock_cache:
        cached_data, cached_time = _stock_cache[ticker]
        if datetime.now() - cached_time < _cache_ttl:
            logger.debug(f"Using cached data for {ticker}")
            return cached_data

    # Try multiple real data sources in order of preference

    # 1. Try Tushare Pro (best for HK stocks - free & fast)
    if TUSHARE_AVAILABLE:
        logger.debug(f"Trying Tushare for {ticker}")
        stock_data = get_stock_data_from_tushare(ticker, code=code)

        if stock_data:
            logger.info(f"✓ Got real data from Tushare for {ticker}")
            # Cache the result
            _stock_cache[ticker] = (stock_data, datetime.now())
            return stock_data

    # 2. Try Finnhub if Tushare failed
    if FINNHUB_AVAILABLE:
        logger.debug(f"Trying Finnhub for {ticker}")
        stock_data = get_stock_data_from_finnhub(ticker)

        if stock_data:
            logger.info(f"✓ Got real data from Finnhub for {ticker}")
            # Cache the result
            _stock_cache[ticker] = (stock_data, datetime.now())
            return stock_data

    # 3. Try AKShare if both Tushare and Finnhub failed
    if AKSHARE_AVAILABLE and code:
        logger.debug(f"Trying AKShare for {ticker} ({code})")
        stock_data = get_stock_data_from_akshare(code, ticker)

        if stock_data:
            logger.info(f"✓ Got real data from AKShare for {ticker}")
            # Cache the result
            _stock_cache[ticker] = (stock_data, datetime.now())
            return stock_data

    # 4. Try web search with GPT-4.1 if all APIs failed
    if settings.OPENAI_API_KEY:
        logger.debug(f"Trying web search for {ticker}")
        stock_data = get_stock_data_from_websearch(ticker, name=name)

        if stock_data:
            logger.info(f"✓ Got real data from web search for {ticker}")
            # Cache the result
            _stock_cache[ticker] = (stock_data, datetime.now())
            return stock_data

    # All real sources failed - return None
    logger.error(f"✗ Cannot find stock data for {ticker} - all sources failed")
    return None


# Demo data removed - return None if all sources fail


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
async def get_all_prices(force_refresh: bool = False):
    """
    Get current prices for all HKEX 18A biotech companies
    Uses parallel processing with caching for fast response times

    Args:
        force_refresh: If True, bypass cache and fetch fresh data

    Returns:
        List of stock data for all companies
    """
    companies = get_hkex_biotech_companies()

    async def fetch_company_data(company: dict) -> dict:
        """Async wrapper to fetch data for a single company"""
        ticker = company["ticker"]
        code = company.get("code")
        name = company["name"]

        logger.info(f"Fetching data for {ticker} ({code}) - {name}")

        # Run the synchronous get_stock_data in a thread pool to avoid blocking
        # Use cache unless force_refresh is True
        stock_data = await asyncio.to_thread(
            get_stock_data, ticker, code=code, name=name, use_cache=(not force_refresh)
        )

        if stock_data:
            # Use name from Tushare if available, otherwise use AAStocks name
            if "name" not in stock_data or not stock_data["name"]:
                stock_data["name"] = name
            return stock_data
        else:
            # Return company info with error
            return {
                "ticker": ticker,
                "name": name,
                "error": "Unable to fetch data",
                "current_price": None,
                "change": None,
                "change_percent": None,
                "last_updated": datetime.now().isoformat(),
            }

    # Fetch all companies in parallel
    logger.info(f"Fetching prices for {len(companies)} companies in parallel")
    results = await asyncio.gather(*[fetch_company_data(company) for company in companies])

    return list(results)


@router.get("/stocks/price/{ticker}")
async def get_price(ticker: str):
    """
    Get current price for a specific ticker

    Args:
        ticker: Stock ticker symbol (e.g., "1801.HK", "ZBIO")

    Returns:
        Stock data for the specified ticker
    """
    # First, check if it's a portfolio company
    from backend.app.services.portfolio import PortfolioService, PORTFOLIO_COMPANIES

    portfolio_company = next((c for c in PORTFOLIO_COMPANIES if c["ticker"] == ticker), None)

    if portfolio_company:
        # It's a portfolio company, fetch data accordingly
        portfolio_service = PortfolioService()

        if portfolio_company['market'] == 'HKEX':
            stock_data = portfolio_service.get_hk_stock_data(ticker, portfolio_company['ts_code'])
        elif portfolio_company['market'] == 'NASDAQ':
            stock_data = portfolio_service.get_us_stock_data(ticker)
        else:
            raise HTTPException(status_code=500, detail=f"Unknown market for {ticker}")

        if not stock_data:
            raise HTTPException(status_code=500, detail=f"Unable to fetch data for {ticker}")

        # Add name and currency
        stock_data["name"] = portfolio_company["name"]
        stock_data["currency"] = portfolio_company["currency"]
        return stock_data

    # If not portfolio company, check HKEX biotech companies
    companies = get_hkex_biotech_companies()
    company = next((c for c in companies if c["ticker"] == ticker), None)

    if not company:
        raise HTTPException(status_code=404, detail=f"Ticker {ticker} not found")

    stock_data = get_stock_data(ticker, code=company.get("code"), name=company["name"])

    if not stock_data:
        raise HTTPException(status_code=500, detail=f"Unable to fetch data for {ticker}")

    stock_data["name"] = company["name"]
    return stock_data


@router.get("/stocks/upcoming-ipos")
async def get_upcoming_ipos(use_latest: bool = True):
    """
    Get HKEX IPO tracker data from S3

    Args:
        use_latest: If True, automatically finds the latest file. If False, uses default file.

    Returns:
        IPO tracker data with company listings
    """
    from backend.app.services.ipo_data import IPODataService

    try:
        service = IPODataService()

        # Get the latest file or use default
        if use_latest:
            try:
                s3_key = service.get_latest_ipo_file()
            except Exception as e:
                logger.warning(f"Could not find latest file, using default: {str(e)}")
                s3_key = None
        else:
            s3_key = None

        # Get IPO data
        result = service.get_ipo_tracker_data(s3_key)

        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to load IPO data"))

        return result

    except Exception as e:
        logger.error(f"Error fetching IPO data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Historical Data Endpoints (Database-backed)
# ============================================================================

@router.get("/stocks/{ticker}/history")
async def get_stock_history(
    ticker: str,
    days: int = 90,
    start_date: str = None,
    end_date: str = None
):
    """
    Get historical price data for a stock from database

    Args:
        ticker: Stock ticker (e.g., "1801.HK")
        days: Number of days to retrieve (default: 90)
        start_date: Start date in YYYY-MM-DD format (optional)
        end_date: End date in YYYY-MM-DD format (optional)

    Returns:
        List of historical price records
    """
    from backend.app.services.stock_data import StockDataService
    from datetime import datetime, date, timedelta

    service = StockDataService()

    # Parse date parameters
    if start_date:
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
    else:
        start = date.today() - timedelta(days=days)

    if end_date:
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
    else:
        end = date.today()

    # Get data from database
    history = service.get_historical_data(
        ticker=ticker,
        start_date=start,
        end_date=end
    )

    # If no data found in database, trigger an update
    if not history:
        logger.info(f"No historical data found for {ticker}, fetching from Tushare...")

        # Convert ticker to Tushare format
        # HK stocks: ticker ends with .HK, format as 5-digit code + .HK (e.g., 02561.HK)
        # US stocks: use ticker as-is (e.g., ZBIO, AAPL)
        if ticker.endswith('.HK'):
            stock_code = ticker.split('.')[0]
            ts_code = f"{stock_code.zfill(5)}.HK"
        else:
            # US stock - use ticker directly
            ts_code = ticker

        # Fetch and store historical data
        service.fetch_and_store_historical_data(
            ticker=ticker,
            ts_code=ts_code,
            start_date=start.strftime('%Y%m%d'),
            end_date=end.strftime('%Y%m%d')
        )

        # Retrieve again
        history = service.get_historical_data(
            ticker=ticker,
            start_date=start,
            end_date=end
        )

    return {
        "ticker": ticker,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "count": len(history),
        "data": history
    }


@router.get("/stocks/{ticker}/returns")
async def get_stock_returns(ticker: str):
    """
    Calculate returns (% gain/loss) for different time periods

    Args:
        ticker: Stock ticker (e.g., "1801.HK")

    Returns:
        Returns for 1W, 1M, 3M, 6M, 1Y periods
    """
    from backend.app.services.stock_data import StockDataService
    from datetime import datetime, date, timedelta

    service = StockDataService()

    try:
        # Get latest price (today)
        latest_data = service.get_historical_data(
            ticker=ticker,
            limit=1
        )

        if not latest_data:
            return {
                "ticker": ticker,
                "error": "No data available",
                "returns": {}
            }

        latest_price = latest_data[0]['close']
        latest_date = datetime.fromisoformat(latest_data[0]['trade_date']).date()

        # Get earliest available date to check if we have enough history
        earliest_date = service.get_latest_date(ticker)  # This gets the earliest date in DB
        all_historical = service.get_historical_data(ticker=ticker)
        if all_historical:
            earliest_date = min(
                datetime.fromisoformat(r['trade_date']).date()
                for r in all_historical
            )
        else:
            earliest_date = latest_date

        # Calculate returns for different periods
        periods = {
            '1W': 7,
            '1M': 30,
            '3M': 90,
            '6M': 180,
            '1Y': 365
        }

        returns = {}

        for period_name, days in periods.items():
            # Get price from N days ago (with a buffer to find closest date)
            target_date = latest_date - timedelta(days=days)
            buffer_start = target_date - timedelta(days=5)  # Look 5 days before
            buffer_end = target_date + timedelta(days=5)    # Look 5 days after

            historical_data = service.get_historical_data(
                ticker=ticker,
                start_date=buffer_start,
                end_date=buffer_end
            )

            if historical_data:
                # Find the record closest to our target date
                # Data is sorted descending (newest first)
                closest_record = None
                min_diff = float('inf')

                for record in historical_data:
                    record_date = datetime.fromisoformat(record['trade_date']).date()
                    diff = abs((record_date - target_date).days)
                    if diff < min_diff:
                        min_diff = diff
                        closest_record = record

                if closest_record:
                    old_price = closest_record['close']
                    old_date = datetime.fromisoformat(closest_record['trade_date']).date()

                    # Calculate return percentage
                    return_pct = ((latest_price - old_price) / old_price) * 100 if old_price else None

                    actual_days = (latest_date - old_date).days
                    days_diff_from_target = (old_date - target_date).days

                    returns[period_name] = {
                        'return': round(return_pct, 2) if return_pct is not None else None,
                        'start_price': round(old_price, 2) if old_price else None,
                        'end_price': round(latest_price, 2),
                        'start_date': old_date.isoformat(),
                        'end_date': latest_date.isoformat(),
                        'days': actual_days,
                        'target_days': days,  # The requested period (7, 30, etc.)
                        'target_date': target_date.isoformat(),  # The ideal date we wanted
                        'days_off_target': days_diff_from_target,  # How many days off from target
                        'since_listed': False
                    }
                else:
                    # No data in buffer range, fall back to "since listed"
                    if all_historical and len(all_historical) > 1:
                        earliest_record = all_historical[-1]  # Last record (oldest)
                        old_price = earliest_record['close']
                        old_date = datetime.fromisoformat(earliest_record['trade_date']).date()
                        return_pct = ((latest_price - old_price) / old_price) * 100 if old_price else None

                        actual_days = (latest_date - old_date).days
                        days_diff_from_target = (old_date - target_date).days

                        returns[period_name] = {
                            'return': round(return_pct, 2) if return_pct is not None else None,
                            'start_price': round(old_price, 2) if old_price else None,
                            'end_price': round(latest_price, 2),
                            'start_date': old_date.isoformat(),
                            'end_date': latest_date.isoformat(),
                            'days': actual_days,
                            'target_days': days,
                            'target_date': target_date.isoformat(),
                            'days_off_target': days_diff_from_target,
                            'since_listed': True
                        }
                    else:
                        returns[period_name] = {
                            'return': None,
                            'start_price': None,
                            'end_price': round(latest_price, 2),
                            'start_date': None,
                            'end_date': latest_date.isoformat(),
                            'days': None,
                            'since_listed': False,
                            'note': 'Insufficient historical data'
                        }
            else:
                # No data in buffer range, fall back to "since listed"
                if all_historical and len(all_historical) > 1:
                    earliest_record = all_historical[-1]  # Last record (oldest)
                    old_price = earliest_record['close']
                    old_date = datetime.fromisoformat(earliest_record['trade_date']).date()
                    return_pct = ((latest_price - old_price) / old_price) * 100 if old_price else None

                    actual_days = (latest_date - old_date).days
                    days_diff_from_target = (old_date - target_date).days

                    returns[period_name] = {
                        'return': round(return_pct, 2) if return_pct is not None else None,
                        'start_price': round(old_price, 2) if old_price else None,
                        'end_price': round(latest_price, 2),
                        'start_date': old_date.isoformat(),
                        'end_date': latest_date.isoformat(),
                        'days': actual_days,
                        'target_days': days,
                        'target_date': target_date.isoformat(),
                        'days_off_target': days_diff_from_target,
                        'since_listed': True
                    }
                else:
                    returns[period_name] = {
                        'return': None,
                        'start_price': None,
                        'end_price': round(latest_price, 2),
                        'start_date': None,
                        'end_date': latest_date.isoformat(),
                        'days': None,
                        'since_listed': False,
                        'note': 'Insufficient historical data'
                    }

        return {
            "ticker": ticker,
            "current_price": round(latest_price, 2),
            "as_of_date": latest_date.isoformat(),
            "returns": returns
        }

    except Exception as e:
        logger.error(f"Error calculating returns for {ticker}: {str(e)}")
        return {
            "ticker": ticker,
            "error": str(e),
            "returns": {}
        }


@router.post("/stocks/{ticker}/update-history")
async def update_stock_history(ticker: str):
    """
    Manually trigger historical data update for a specific stock

    Args:
        ticker: Stock ticker (e.g., "1801.HK")

    Returns:
        Update status and statistics
    """
    from backend.app.services.stock_data import StockDataService

    service = StockDataService()

    # Convert ticker to Tushare format
    if ticker.endswith('.HK'):
        stock_code = ticker.split('.')[0]
        ts_code = f"{stock_code.zfill(5)}.HK"
    else:
        # US stock - use ticker directly
        ts_code = ticker

    try:
        new_records = service.update_incremental(ticker, ts_code)

        return {
            "status": "success",
            "ticker": ticker,
            "new_records": new_records,
            "message": f"Updated {ticker} with {new_records} new records"
        }
    except Exception as e:
        logger.error(f"Error updating {ticker}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stocks/bulk-update-history")
async def bulk_update_all_history():
    """
    Update historical data for all HKEX 18A stocks incrementally
    Only fetches new trading days since last update

    Returns:
        Update statistics
    """
    from backend.app.services.stock_data import StockDataService

    service = StockDataService()
    companies = get_hkex_biotech_companies()

    # Prepare list of (ticker, ts_code) tuples
    tickers = []
    for company in companies:
        ticker = company["ticker"]
        code = company.get("code")

        if code:
            ts_code = f"{code}.HK"
        else:
            stock_code = ticker.split('.')[0]
            ts_code = f"{stock_code.zfill(5)}.HK"

        tickers.append((ticker, ts_code))

    # Run bulk update
    stats = service.bulk_update_all_stocks(tickers)

    return {
        "status": "success",
        "statistics": stats,
        "message": f"Updated {stats['updated']} stocks with {stats['new_records']} new records"
    }


@router.get("/stocks/history/stats")
async def get_history_stats():
    """
    Get statistics about stored historical data

    Returns:
        Database statistics
    """
    from backend.app.services.stock_data import StockDataService
    from backend.app.database import get_session_local
    from sqlalchemy import func
    from backend.app.models.stock import StockDaily

    session_local = get_session_local()
    db = session_local()

    try:
        # Total records
        total_records = db.query(func.count(StockDaily.id)).scalar()

        # Number of unique stocks
        unique_stocks = db.query(func.count(func.distinct(StockDaily.ticker))).scalar()

        # Date range
        min_date = db.query(func.min(StockDaily.trade_date)).scalar()
        max_date = db.query(func.max(StockDaily.trade_date)).scalar()

        # Records per stock
        stock_counts = db.query(
            StockDaily.ticker,
            func.count(StockDaily.id).label('count'),
            func.min(StockDaily.trade_date).label('earliest'),
            func.max(StockDaily.trade_date).label('latest')
        ).group_by(StockDaily.ticker).all()

        return {
            "total_records": total_records,
            "unique_stocks": unique_stocks,
            "date_range": {
                "earliest": min_date.isoformat() if min_date else None,
                "latest": max_date.isoformat() if max_date else None
            },
            "stocks": [
                {
                    "ticker": row.ticker,
                    "record_count": row.count,
                    "earliest_date": row.earliest.isoformat() if row.earliest else None,
                    "latest_date": row.latest.isoformat() if row.latest else None
                }
                for row in stock_counts
            ]
        }
    finally:
        db.close()


@router.post("/stocks/{ticker}/backfill-history")
async def backfill_single_stock_history(ticker: str, days: int = 365):
    """
    Backfill older historical data for a specific stock.
    Fetches data going backwards from the earliest date we have.

    Args:
        ticker: Stock ticker (e.g., "1801.HK")
        days: Number of days to backfill (default: 365)

    Returns:
        Status and number of new records added
    """
    from backend.app.services.stock_data import StockDataService

    try:
        # Extract stock code and convert to Tushare format
        if ticker.endswith('.HK'):
            stock_code = ticker.split('.')[0]
            ts_code = f"{stock_code.zfill(5)}.HK"
        else:
            # US stock - use ticker directly
            ts_code = ticker

        service = StockDataService()
        new_records = service.backfill_historical_data(ticker, ts_code, days)

        return {
            "status": "success",
            "ticker": ticker,
            "ts_code": ts_code,
            "days_requested": days,
            "new_records": new_records,
            "message": f"Backfilled {ticker} with {new_records} new records"
        }
    except Exception as e:
        logger.error(f"Error backfilling {ticker}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stocks/bulk-backfill-history")
async def bulk_backfill_all_history(days: int = 365):
    """
    Backfill older historical data for all HKEX 18A biotech stocks.
    Goes backwards from the earliest date we have for each stock.

    Args:
        days: Number of days to backfill for each stock (default: 365)

    Returns:
        Statistics about the backfill operation
    """
    from backend.app.services.stock_data import StockDataService

    try:
        # Get all biotech companies
        companies = get_hkex_biotech_companies()

        # Create list of (ticker, ts_code) tuples
        tickers = [(company["ticker"], f"{company['code']}.HK") for company in companies]

        service = StockDataService()
        stats = service.bulk_backfill_all_stocks(tickers, days)

        logger.info(f"Bulk backfill completed: {stats}")

        return {
            "status": "success",
            "days_requested": days,
            "statistics": stats
        }
    except Exception as e:
        logger.error(f"Error during bulk backfill: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Portfolio Companies Endpoints
# ============================================================================

@router.get("/stocks/portfolio")
async def get_portfolio_companies(force_refresh: bool = False):
    """
    Get portfolio companies data (both HKEX and NASDAQ)

    Args:
        force_refresh: If True, bypass cache and fetch fresh data

    Returns:
        List of portfolio companies with current prices and performance
    """
    from backend.app.services.portfolio import PortfolioService

    try:
        service = PortfolioService()
        companies = service.get_portfolio_companies(use_cache=(not force_refresh))

        return {
            "success": True,
            "count": len(companies),
            "companies": companies,
            "last_updated": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error fetching portfolio companies: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

