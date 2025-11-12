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
    logging.warning("AKShare not available")

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    logging.warning("yfinance not available")

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
        import os
        import json

        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

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


def get_stock_data(ticker: str, code: str = None, name: str = None, use_cache: bool = True) -> Dict[str, Any]:
    """
    Fetch stock data with caching, tries multiple sources: yfinance -> AKShare -> Web Search -> demo data

    Args:
        ticker: Stock ticker symbol (e.g., "1801.HK")
        code: HK stock code in 5-digit format (e.g., "01801")
        name: Company name for web search (optional)
        use_cache: Whether to use cached data

    Returns:
        Dictionary containing stock data
    """
    # Check cache first
    if use_cache and ticker in _stock_cache:
        cached_data, cached_time = _stock_cache[ticker]
        if datetime.now() - cached_time < _cache_ttl:
            logger.debug(f"Using cached data for {ticker}")
            return cached_data

    # Try multiple real data sources in order of preference

    # 1. Try yfinance (usually most reliable for HK stocks)
    if YFINANCE_AVAILABLE:
        logger.debug(f"Trying yfinance for {ticker}")
        stock_data = get_stock_data_from_yfinance(ticker)

        if stock_data:
            logger.info(f"✓ Got real data from yfinance for {ticker}")
            # Cache the result
            _stock_cache[ticker] = (stock_data, datetime.now())
            return stock_data

    # 2. Try AKShare if yfinance failed
    if AKSHARE_AVAILABLE and code:
        logger.debug(f"Trying AKShare for {ticker} ({code})")
        stock_data = get_stock_data_from_akshare(code, ticker)

        if stock_data:
            logger.info(f"✓ Got real data from AKShare for {ticker}")
            # Cache the result
            _stock_cache[ticker] = (stock_data, datetime.now())
            return stock_data

    # 3. Try web search with GPT-4 if both APIs failed
    logger.debug(f"Trying web search for {ticker}")
    stock_data = get_stock_data_from_websearch(ticker, name=name)

    if stock_data:
        logger.info(f"✓ Got real data from web search for {ticker}")
        # Cache the result
        _stock_cache[ticker] = (stock_data, datetime.now())
        return stock_data

    # 4. Fall back to demo data only if ALL real sources failed
    logger.warning(f"⚠ All real data sources failed for {ticker}, using demo data")
    return get_demo_stock_data(ticker)


def get_demo_stock_data(ticker: str) -> Dict[str, Any]:
    """
    Get demo/fallback stock data when AKShare fails

    For tickers with predefined demo data, use that.
    For others, generate realistic-looking demo data based on ticker.

    Args:
        ticker: Stock ticker symbol

    Returns:
        Dictionary containing demo stock data
    """
    # Use predefined demo data if available
    if ticker in DEMO_STOCK_DATA:
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
            "data_source": "Demo Data (All real sources unavailable)"
        }
    else:
        # Generate demo data for tickers without predefined data
        # Use ticker hash to get consistent "random" prices
        import hashlib
        ticker_hash = int(hashlib.md5(ticker.encode()).hexdigest()[:8], 16)

        # Generate price between HKD 5-100 based on ticker hash
        base_price = 5 + (ticker_hash % 950) / 10.0

        # Generate change between -5% to +5%
        change_pct = ((ticker_hash % 1000) / 100.0) - 5.0
        change = base_price * (change_pct / 100.0)

        previous_close = base_price - change
        current_price = base_price

        # Generate volume between 100K - 50M
        volume = 100000 + (ticker_hash % 49900000)

        # Generate market cap between 100M - 50B
        market_cap = 100000000 + (ticker_hash % 49900000000)

        stock_data = {
            "ticker": ticker,
            "current_price": current_price,
            "open": current_price - 0.5,
            "previous_close": previous_close,
            "day_high": current_price + abs(change) * 0.8,
            "day_low": current_price - abs(change) * 0.6,
            "volume": volume,
            "change": change,
            "change_percent": change_pct,
            "market_cap": market_cap,
            "currency": "HKD",
            "last_updated": datetime.now().isoformat(),
            "data_source": "Demo Data (All real sources unavailable)"
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

        stock_data = get_stock_data(ticker, code=code, name=name, use_cache=True)

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

        # Add small delay between requests to avoid rate limiting (except for last item)
        if i < len(companies) - 1:
            await asyncio.sleep(0.2)  # 200ms delay between requests

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

    stock_data = get_stock_data(ticker, code=company.get("code"), name=company["name"])

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
