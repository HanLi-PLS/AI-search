"""
Portfolio Companies Service - Track specific portfolio companies across markets
"""
import logging
import tushare as ts
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

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
        Get HK stock data from Tushare

        Args:
            ticker: Stock ticker (e.g., "2561.HK")
            ts_code: Tushare code (e.g., "02561.HK")

        Returns:
            Stock data dictionary
        """
        try:
            pro = ts.pro_api()

            # Get latest trading data
            df = pro.hk_daily(ts_code=ts_code, start_date='', end_date='')

            if df is None or df.empty:
                logger.warning(f"No data returned from Tushare for {ticker}")
                return None

            # Get the most recent data
            latest = df.iloc[0]

            return {
                "ticker": ticker,
                "ts_code": ts_code,
                "current_price": float(latest['close']) if latest['close'] else None,
                "open": float(latest['open']) if latest['open'] else None,
                "high": float(latest['high']) if latest['high'] else None,
                "low": float(latest['low']) if latest['low'] else None,
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
            logger.error(f"Error fetching HK stock data for {ticker}: {str(e)}")
            return None

    def get_us_stock_data(self, ticker: str) -> Dict[str, Any]:
        """
        Get US stock data from Tushare (preferred) or yfinance (fallback)

        Args:
            ticker: Stock ticker (e.g., "ZBIO")

        Returns:
            Stock data dictionary
        """
        # Try Tushare first (more reliable for NASDAQ stocks)
        try:
            pro = ts.pro_api()

            # Tushare uses .O suffix for NASDAQ stocks
            ts_code = f"{ticker}.O"

            # Get recent trading data (last 30 days to ensure we have data)
            from datetime import date, timedelta
            end_date = date.today().strftime('%Y%m%d')
            start_date = (date.today() - timedelta(days=30)).strftime('%Y%m%d')

            df = pro.us_daily(ts_code=ts_code, start_date=start_date, end_date=end_date)

            if df is not None and not df.empty:
                # Data is sorted by date descending, so first row is most recent
                latest = df.iloc[0]
                previous = df.iloc[1] if len(df) > 1 else latest

                logger.info(f"Successfully fetched {ticker} data from Tushare")

                return {
                    "ticker": ticker,
                    "ts_code": ts_code,
                    "current_price": float(latest['close']) if latest['close'] else None,
                    "open": float(latest['open']) if latest['open'] else None,
                    "high": float(latest['high']) if latest['high'] else None,
                    "low": float(latest['low']) if latest['low'] else None,
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

        # Fallback to yfinance
        try:
            import yfinance as yf

            stock = yf.Ticker(ticker)
            hist = stock.history(period="5d")

            if hist.empty:
                logger.warning(f"No data returned from yfinance for {ticker}")
                return None

            latest = hist.iloc[-1]
            previous = hist.iloc[-2] if len(hist) > 1 else latest

            # Try to get market cap from fast_info
            market_cap = None
            try:
                if hasattr(stock, 'fast_info'):
                    market_cap = stock.fast_info.get('market_cap', None)
            except Exception as e:
                logger.debug(f"Could not get fast_info for {ticker}: {e}")

            logger.info(f"Successfully fetched {ticker} data from yfinance")

            return {
                "ticker": ticker,
                "ts_code": ticker,
                "current_price": float(latest['Close']) if 'Close' in latest else None,
                "open": float(latest['Open']) if 'Open' in latest else None,
                "high": float(latest['High']) if 'High' in latest else None,
                "low": float(latest['Low']) if 'Low' in latest else None,
                "previous_close": float(previous['Close']) if 'Close' in previous else None,
                "volume": int(latest['Volume']) if 'Volume' in latest else None,
                "market_cap": market_cap,
                "change": None,  # Calculate below
                "change_percent": None,  # Calculate below
                "data_source": "Yahoo Finance",
                "last_updated": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Both Tushare and yfinance failed for {ticker}: {str(e)}")
            return None

    def get_portfolio_companies(self) -> List[Dict[str, Any]]:
        """
        Get data for all portfolio companies

        Returns:
            List of portfolio company data
        """
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

        return results
