"""
Portfolio Companies Service - Track specific portfolio companies across markets
"""
import logging
import tushare as ts
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Cache for portfolio companies data
_portfolio_cache = None
_portfolio_cache_time = None
_portfolio_cache_ttl = timedelta(hours=12)  # Cache for 12 hours

# Portfolio companies configuration
PORTFOLIO_COMPANIES = [
    {
        "name": "Visen Pharmaceuticals",
        "ticker": "2561.HK",
        "ts_code": "02561.HK",
        "market": "HKEX",
        "currency": "HKD",
        "description": "Biopharmaceutical company"
    },
    {
        "name": "Zenas Biopharma",
        "ticker": "ZBIO",
        "ts_code": "ZBIO",  # For NASDAQ stocks, ticker = ts_code
        "market": "NASDAQ",
        "currency": "USD",
        "description": "Clinical-stage biopharmaceutical company"
    }
]


class PortfolioService:
    """Service for tracking portfolio companies"""

    def __init__(self):
        """Initialize portfolio service"""
        logger.info("Portfolio Service initialized")

    def get_hk_stock_data(self, ticker: str, ts_code: str) -> Dict[str, Any]:
        """
        Get HK stock data - tries CapIQ first, falls back to Tushare

        Args:
            ticker: Stock ticker (e.g., "2561.HK")
            ts_code: Tushare code (e.g., "02561.HK")

        Returns:
            Stock data dictionary
        """
        # Try CapIQ first (most comprehensive data)
        try:
            from backend.app.services.capiq_data import get_capiq_service

            capiq_service = get_capiq_service()
            if capiq_service.available:
                logger.debug(f"Trying CapIQ for {ticker}")
                capiq_data = capiq_service.get_company_data(ticker, market="HK")

                if capiq_data and capiq_data.get('price_close'):
                    logger.info(f"✓ Got HK stock data from CapIQ for {ticker}")

                    # Convert CapIQ data to standard format
                    change = None
                    change_percent = None
                    if capiq_data.get('price_close') and capiq_data.get('price_open'):
                        change = capiq_data['price_close'] - capiq_data['price_open']
                        change_percent = (change / capiq_data['price_open'] * 100) if capiq_data['price_open'] != 0 else 0

                    return {
                        "ticker": ticker,
                        "ts_code": ts_code,
                        "current_price": capiq_data.get('price_close'),
                        "open": capiq_data.get('price_open'),
                        "day_high": capiq_data.get('price_high'),
                        "day_low": capiq_data.get('price_low'),
                        "previous_close": capiq_data.get('price_close'),  # Will be updated from DB if available
                        "volume": capiq_data.get('volume'),
                        "market_cap": capiq_data.get('market_cap'),
                        "change": change,
                        "change_percent": change_percent,
                        "trade_date": capiq_data.get('pricing_date'),
                        "ttm_revenue": capiq_data.get('ttm_revenue'),
                        "ps_ratio": capiq_data.get('ps_ratio'),
                        "listing_date": capiq_data.get('listing_date'),
                        "data_source": "CapIQ",
                        "last_updated": datetime.now().isoformat()
                    }
        except Exception as e:
            logger.warning(f"CapIQ failed for {ticker}, falling back to Tushare: {str(e)}")

        # Fallback to Tushare
        try:
            logger.debug(f"Trying Tushare for {ticker}")
            pro = ts.pro_api()

            # Get latest trading data
            df = pro.hk_daily(ts_code=ts_code, start_date='', end_date='')

            if df is None or df.empty:
                logger.warning(f"No data returned from Tushare for {ticker}")
                return None

            # Get the most recent data
            latest = df.iloc[0]

            logger.info(f"✓ Got HK stock data from Tushare for {ticker}")

            return {
                "ticker": ticker,
                "ts_code": ts_code,
                "current_price": float(latest['close']) if latest['close'] else None,
                "open": float(latest['open']) if latest['open'] else None,
                "day_high": float(latest['high']) if latest['high'] else None,
                "day_low": float(latest['low']) if latest['low'] else None,
                "previous_close": float(latest['pre_close']) if latest['pre_close'] else None,
                "volume": float(latest['vol']) if latest['vol'] else None,
                "amount": float(latest['amount']) if latest['amount'] else None,
                "change": float(latest['change']) if 'change' in latest and latest['change'] else None,
                "change_percent": float(latest['pct_chg']) if 'pct_chg' in latest and latest['pct_chg'] else None,
                "trade_date": latest['trade_date'],
                "data_source": "Tushare Pro",
                "last_updated": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error fetching HK stock data for {ticker} from both CapIQ and Tushare: {str(e)}")
            return None

    def get_us_stock_data(self, ticker: str) -> Dict[str, Any]:
        """
        Get US stock data - tries CapIQ first, falls back to Finnhub/Tushare/yfinance

        Args:
            ticker: Stock ticker (e.g., "ZBIO")

        Returns:
            Stock data dictionary
        """
        # Try CapIQ first (most comprehensive data)
        try:
            from backend.app.services.capiq_data import get_capiq_service

            capiq_service = get_capiq_service()
            if capiq_service.available:
                logger.debug(f"Trying CapIQ for US stock {ticker}")
                capiq_data = capiq_service.get_company_data(ticker, market="US")

                if capiq_data and capiq_data.get('price_close'):
                    logger.info(f"✓ Got US stock data from CapIQ for {ticker}")

                    # Convert CapIQ data to standard format
                    change = None
                    change_percent = None
                    if capiq_data.get('price_close') and capiq_data.get('price_open'):
                        change = capiq_data['price_close'] - capiq_data['price_open']
                        change_percent = (change / capiq_data['price_open'] * 100) if capiq_data['price_open'] != 0 else 0

                    return {
                        "ticker": ticker,
                        "ts_code": ticker,
                        "current_price": capiq_data.get('price_close'),
                        "open": capiq_data.get('price_open'),
                        "day_high": capiq_data.get('price_high'),
                        "day_low": capiq_data.get('price_low'),
                        "previous_close": capiq_data.get('price_close'),  # Will be updated from DB if available
                        "volume": capiq_data.get('volume'),
                        "market_cap": capiq_data.get('market_cap'),
                        "change": change,
                        "change_percent": change_percent,
                        "trade_date": capiq_data.get('pricing_date'),
                        "ttm_revenue": capiq_data.get('ttm_revenue'),
                        "ps_ratio": capiq_data.get('ps_ratio'),
                        "listing_date": capiq_data.get('listing_date'),
                        "data_source": "CapIQ",
                        "last_updated": datetime.now().isoformat()
                    }
        except Exception as e:
            logger.warning(f"CapIQ failed for {ticker}, falling back to Finnhub: {str(e)}")

        # Try Finnhub as fallback (reliable for NASDAQ stocks)
        try:
            import finnhub
            from backend.app.config import settings

            if settings.FINNHUB_API_KEY:
                finnhub_client = finnhub.Client(api_key=settings.FINNHUB_API_KEY)

                # Get quote (current price)
                quote = finnhub_client.quote(ticker)

                # Get company profile for additional info
                try:
                    profile = finnhub_client.company_profile2(symbol=ticker)
                    market_cap = profile.get('marketCapitalization', None)
                    if market_cap:
                        market_cap = market_cap * 1_000_000  # Finnhub returns in millions
                except:
                    market_cap = None

                if quote and quote.get('c'):  # 'c' is current price
                    current_price = float(quote['c'])
                    previous_close = float(quote['pc']) if quote.get('pc') else None
                    change = float(quote['d']) if quote.get('d') else None
                    change_percent = float(quote['dp']) if quote.get('dp') else None

                    logger.info(f"Successfully fetched {ticker} data from Finnhub")

                    return {
                        "ticker": ticker,
                        "ts_code": ticker,
                        "current_price": current_price,
                        "open": float(quote['o']) if quote.get('o') else None,
                        "day_high": float(quote['h']) if quote.get('h') else None,
                        "day_low": float(quote['l']) if quote.get('l') else None,
                        "previous_close": previous_close,
                        "volume": None,  # Not available in quote endpoint
                        "market_cap": market_cap,
                        "change": change,
                        "change_percent": change_percent,
                        "data_source": "Finnhub",
                        "last_updated": datetime.now().isoformat()
                    }
        except Exception as e:
            logger.warning(f"Finnhub failed for {ticker}, trying Tushare: {str(e)}")

        # Try Tushare as fallback
        try:
            pro = ts.pro_api()
            # Tushare uses ticker directly for US stocks (e.g., 'ZBIO', not 'ZBIO.O')
            ts_code = ticker

            from datetime import date, timedelta
            end_date = date.today().strftime('%Y%m%d')
            start_date = (date.today() - timedelta(days=30)).strftime('%Y%m%d')

            df = pro.us_daily(ts_code=ts_code, start_date=start_date, end_date=end_date)

            if df is not None and not df.empty:
                latest = df.iloc[0]
                previous = df.iloc[1] if len(df) > 1 else latest

                logger.info(f"Successfully fetched {ticker} data from Tushare")

                return {
                    "ticker": ticker,
                    "ts_code": ts_code,
                    "current_price": float(latest['close']) if latest['close'] else None,
                    "open": float(latest['open']) if latest['open'] else None,
                    "day_high": float(latest['high']) if latest['high'] else None,
                    "day_low": float(latest['low']) if latest['low'] else None,
                    "previous_close": float(previous['close']) if previous['close'] else None,
                    "volume": float(latest['vol']) if latest['vol'] else None,
                    "change": float(latest['close'] - previous['close']) if (latest['close'] and previous['close']) else None,
                    "change_percent": float((latest['close'] - previous['close']) / previous['close'] * 100) if (latest['close'] and previous['close']) else None,
                    "trade_date": latest['trade_date'],
                    "data_source": "Tushare Pro (US)",
                    "last_updated": datetime.now().isoformat()
                }
        except Exception as e:
            logger.warning(f"Tushare failed for {ticker}, trying yfinance: {str(e)}")

        # Last resort: yfinance
        try:
            import yfinance as yf

            stock = yf.Ticker(ticker)
            hist = stock.history(period="5d")

            if hist.empty:
                logger.warning(f"No data returned from yfinance for {ticker}")
                return None

            latest = hist.iloc[-1]
            previous = hist.iloc[-2] if len(hist) > 1 else latest

            logger.info(f"Successfully fetched {ticker} data from yfinance")

            return {
                "ticker": ticker,
                "ts_code": ticker,
                "current_price": float(latest['Close']) if 'Close' in latest else None,
                "open": float(latest['Open']) if 'Open' in latest else None,
                "day_high": float(latest['High']) if 'High' in latest else None,
                "day_low": float(latest['Low']) if 'Low' in latest else None,
                "previous_close": float(previous['Close']) if 'Close' in previous else None,
                "volume": int(latest['Volume']) if 'Volume' in latest else None,
                "change": None,  # Calculate below
                "change_percent": None,  # Calculate below
                "data_source": "Yahoo Finance",
                "last_updated": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"All data sources failed for {ticker}: {str(e)}")
            return None

    def get_portfolio_companies(self, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Get data for all portfolio companies

        Args:
            use_cache: Whether to use cached data (default: True)

        Returns:
            List of portfolio company data
        """
        global _portfolio_cache, _portfolio_cache_time

        # Check cache first
        if use_cache and _portfolio_cache is not None and _portfolio_cache_time is not None:
            cache_age = datetime.now() - _portfolio_cache_time
            if cache_age < _portfolio_cache_ttl:
                logger.info(f"Using cached portfolio data (age: {cache_age})")
                return _portfolio_cache

        logger.info("Fetching fresh portfolio data from APIs...")
        results = []

        for company in PORTFOLIO_COMPANIES:
            try:
                # Fetch stock data based on market
                if company['market'] == 'HKEX':
                    stock_data = self.get_hk_stock_data(company['ticker'], company['ts_code'])
                elif company['market'] == 'NASDAQ':
                    stock_data = self.get_us_stock_data(company['ticker'])
                else:
                    logger.warning(f"Unknown market for {company['name']}: {company['market']}")
                    stock_data = None

                if stock_data:
                    # Merge company info with stock data
                    result = {**company, **stock_data}

                    # Calculate change if not already present
                    if result['change'] is None and result['current_price'] and result['previous_close']:
                        result['change'] = result['current_price'] - result['previous_close']

                    if result['change_percent'] is None and result['current_price'] and result['previous_close']:
                        result['change_percent'] = (result['change'] / result['previous_close']) * 100

                    # Calculate intraday change (close vs open) from DB if available
                    # This ensures consistency with the main stock tracker
                    try:
                        from backend.app.api.routes.stocks import calculate_daily_change_from_db
                        result = calculate_daily_change_from_db(company['ticker'], result)
                    except Exception as e:
                        logger.warning(f"Could not calculate DB-based changes for {company['ticker']}: {str(e)}")
                        # Fallback: calculate intraday from current data if available
                        if result.get('current_price') and result.get('open'):
                            intraday_change = result['current_price'] - result['open']
                            intraday_change_percent = (intraday_change / result['open'] * 100) if result['open'] != 0 else 0
                            result['intraday_change'] = intraday_change
                            result['intraday_change_percent'] = intraday_change_percent

                    results.append(result)
                else:
                    # Add company with error state
                    results.append({
                        **company,
                        "error": "Unable to fetch data",
                        "current_price": None,
                        "change": None,
                        "change_percent": None,
                        "last_updated": datetime.now().isoformat()
                    })

            except Exception as e:
                logger.error(f"Error processing {company['name']}: {str(e)}")
                results.append({
                    **company,
                    "error": str(e),
                    "current_price": None,
                    "change": None,
                    "change_percent": None,
                    "last_updated": datetime.now().isoformat()
                })

        # Update cache
        _portfolio_cache = results
        _portfolio_cache_time = datetime.now()
        logger.info(f"Portfolio cache updated with {len(results)} companies")

        return results
