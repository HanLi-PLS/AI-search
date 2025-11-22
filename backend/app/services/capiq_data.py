"""
CapIQ Data Service for accessing Capital IQ data from Snowflake
Provides comprehensive company data, fundamentals, and market information
"""
import logging
from typing import Optional, List, Dict, Any
import pandas as pd
from backend.app.config import settings

logger = logging.getLogger(__name__)

# Global connection instance
_snowflake_conn = None


def get_snowflake_connection():
    """
    Get or create Snowflake connection
    Supports both password and key-pair authentication
    Fetches credentials from AWS Secrets Manager if configured
    Returns None if CapIQ is not configured
    """
    global _snowflake_conn

    if not settings.USE_CAPIQ_DATA:
        return None

    if _snowflake_conn is None:
        try:
            import snowflake.connector
            from cryptography.hazmat.backends import default_backend
            from cryptography.hazmat.primitives import serialization

            # Get credentials - from AWS Secrets Manager or environment variables
            snowflake_user = settings.SNOWFLAKE_USER
            snowflake_password = settings.SNOWFLAKE_PASSWORD
            snowflake_account = settings.SNOWFLAKE_ACCOUNT

            if settings.USE_AWS_SECRETS:
                # Fetch Snowflake credentials from AWS Secrets Manager
                try:
                    from backend.app.utils.aws_secrets import get_secret
                    logger.info("Fetching Snowflake credentials from AWS Secrets Manager")

                    if settings.AWS_SECRET_NAME_SNOWFLAKE_USER:
                        snowflake_user = get_secret(settings.AWS_SECRET_NAME_SNOWFLAKE_USER, settings.AWS_REGION).strip()
                    if settings.AWS_SECRET_NAME_SNOWFLAKE_PASSWORD:
                        snowflake_password = get_secret(settings.AWS_SECRET_NAME_SNOWFLAKE_PASSWORD, settings.AWS_REGION).strip()
                    if settings.AWS_SECRET_NAME_SNOWFLAKE_ACCOUNT:
                        snowflake_account = get_secret(settings.AWS_SECRET_NAME_SNOWFLAKE_ACCOUNT, settings.AWS_REGION).strip()

                    logger.info(f"Successfully fetched Snowflake credentials for user: {snowflake_user}")
                except Exception as e:
                    logger.error(f"Failed to fetch Snowflake credentials from AWS Secrets Manager: {str(e)}")
                    logger.info("Falling back to environment variables")

            # Build connection parameters
            conn_params = {
                "user": snowflake_user,
                "account": snowflake_account,
                "warehouse": settings.SNOWFLAKE_WAREHOUSE,
                "database": settings.SNOWFLAKE_DATABASE,
                "schema": settings.SNOWFLAKE_SCHEMA,
            }

            # Add role if specified
            if settings.SNOWFLAKE_ROLE:
                conn_params["role"] = settings.SNOWFLAKE_ROLE

            # Choose authentication method
            if settings.SNOWFLAKE_PRIVATE_KEY_PATH:
                # Key-pair authentication
                logger.info("Using key-pair authentication for Snowflake")
                with open(settings.SNOWFLAKE_PRIVATE_KEY_PATH, "rb") as key_file:
                    if settings.SNOWFLAKE_PRIVATE_KEY_PASSPHRASE:
                        p_key = serialization.load_pem_private_key(
                            key_file.read(),
                            password=settings.SNOWFLAKE_PRIVATE_KEY_PASSPHRASE.encode(),
                            backend=default_backend()
                        )
                    else:
                        p_key = serialization.load_pem_private_key(
                            key_file.read(),
                            password=None,
                            backend=default_backend()
                        )

                pkb = p_key.private_bytes(
                    encoding=serialization.Encoding.DER,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                )
                conn_params["private_key"] = pkb
            elif snowflake_password:
                # Password authentication
                logger.info("Using password authentication for Snowflake")
                conn_params["password"] = snowflake_password
            else:
                logger.error("No authentication method configured (need password or private key)")
                return None

            _snowflake_conn = snowflake.connector.connect(**conn_params)
            logger.info(f"Connected to Snowflake CapIQ: {settings.SNOWFLAKE_DATABASE}.{settings.SNOWFLAKE_SCHEMA}")
        except ImportError as e:
            logger.error(f"Missing dependency: {str(e)}. Install with: pip install snowflake-connector-python cryptography")
            return None
        except Exception as e:
            logger.error(f"Failed to connect to Snowflake CapIQ: {str(e)}")
            return None

    return _snowflake_conn


class CapIQDataService:
    """Service for accessing Capital IQ data from Snowflake"""

    def __init__(self):
        self.conn = get_snowflake_connection()
        self.available = self.conn is not None

    def test_connection(self) -> Dict[str, Any]:
        """
        Test Snowflake CapIQ connection and return status

        Returns:
            Dict with connection status and available tables and views
        """
        if not self.available:
            return {
                "success": False,
                "message": "CapIQ not configured or connection failed",
                "configured": settings.USE_CAPIQ_DATA
            }

        try:
            cursor = self.conn.cursor()
            all_objects = []

            # Get tables
            cursor.execute("SHOW TABLES IN SCHEMA")
            tables = cursor.fetchall()
            table_names = [row[1] for row in tables]  # Table name is in second column
            all_objects.extend([{"name": name, "type": "table"} for name in table_names])

            # Get views
            cursor.execute("SHOW VIEWS IN SCHEMA")
            views = cursor.fetchall()
            view_names = [row[1] for row in views]  # View name is in second column
            all_objects.extend([{"name": name, "type": "view"} for name in view_names])

            cursor.close()

            return {
                "success": True,
                "message": f"Connected to {settings.SNOWFLAKE_DATABASE}.{settings.SNOWFLAKE_SCHEMA}",
                "tables": table_names,
                "views": view_names,
                "all_objects": all_objects,
                "table_count": len(table_names),
                "view_count": len(view_names),
                "total_count": len(all_objects)
            }
        except Exception as e:
            logger.error(f"CapIQ connection test failed: {str(e)}")
            return {
                "success": False,
                "message": f"Connection test failed: {str(e)}"
            }

    def search_companies(self, query: str, limit: int = 10, market: str = None) -> List[Dict[str, Any]]:
        """
        Search for companies by name or ticker across all markets

        Args:
            query: Search query (company name or ticker)
            limit: Maximum number of results
            market: Optional market filter ('US', 'HK', or None for all)

        Returns:
            List of matching companies with basic info
        """
        if not self.available:
            return []

        try:
            # Build market filter using exact exchange names discovered from CapIQ
            market_filter = ""
            if market == "US":
                # Use exact exchange names for US markets (Nasdaq and NYSE)
                market_filter = """AND (
                    ex.exchangename = 'Nasdaq Global Select'
                    OR ex.exchangename LIKE 'New York Stock Exchange%%'
                    OR ex.exchangesymbol IN ('NasdaqGS', 'NYSE', 'NYSEArca')
                )"""
            elif market == "HK":
                # Hong Kong Stock Exchange
                market_filter = "AND ex.exchangename = 'The Stock Exchange of Hong Kong Ltd.'"

            sql = f"""
            SELECT DISTINCT
                c.companyid,
                c.companyname,
                c.webpage,
                ti.tickersymbol,
                ex.exchangesymbol,
                ex.exchangename,
                s.subtypevalue as industry
            FROM ciqcompany c
            INNER JOIN ciqsecurity sec
                ON c.companyid = sec.companyid
            INNER JOIN ciqtradingitem ti
                ON sec.securityid = ti.securityid
            INNER JOIN ciqexchange ex
                ON ti.exchangeid = ex.exchangeid
            LEFT JOIN ciqCompanyIndustryTree tree
                ON tree.companyid = c.companyid AND tree.primaryflag = 1
            LEFT JOIN ciqSubType s
                ON s.subTypeId = tree.subTypeId
            WHERE c.companyTypeId = 4  -- public companies only
                AND c.companyStatusTypeId IN (1, 20)  -- operating/active
                AND sec.primaryflag = 1
                AND (UPPER(c.companyname) LIKE UPPER(%s) OR UPPER(ti.tickersymbol) LIKE UPPER(%s))
                {market_filter}
            LIMIT {limit}
            """

            search_pattern = f"%{query}%"
            cursor = self.conn.cursor()
            cursor.execute(sql, [search_pattern, search_pattern])
            rows = cursor.fetchall()
            cursor.close()

            results = []
            for row in rows:
                results.append({
                    "companyid": row[0],
                    "companyname": row[1],
                    "webpage": row[2],
                    "ticker": row[3],
                    "exchange_symbol": row[4],
                    "exchange_name": row[5],
                    "industry": row[6]
                })

            return results
        except Exception as e:
            logger.error(f"Company search failed: {str(e)}")
            return []

    def get_company_data(self, ticker: str, market: str = "US", exchange_name: str = None) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive company data from CapIQ including latest price and market cap

        Args:
            ticker: Stock ticker symbol
            market: Market identifier (US, HK, etc.)
            exchange_name: Optional specific exchange name

        Returns:
            Company data dictionary or None if not found
        """
        if not self.available:
            return None

        try:
            # Build market filter using exact exchange names discovered from CapIQ
            market_filter = ""
            if exchange_name:
                market_filter = f"AND ex.exchangename = '{exchange_name}'"
            elif market == "US":
                # Use exact exchange names for US markets (Nasdaq and NYSE)
                market_filter = """AND (
                    ex.exchangename = 'Nasdaq Global Select'
                    OR ex.exchangename LIKE 'New York Stock Exchange%%'
                    OR ex.exchangesymbol IN ('NasdaqGS', 'NYSE', 'NYSEArca')
                )"""
            elif market == "HK":
                # Hong Kong Stock Exchange
                market_filter = "AND ex.exchangename = 'The Stock Exchange of Hong Kong Ltd.'"

            # Normalize ticker for HK market (CapIQ stores as numbers without .HK suffix)
            query_ticker = ticker
            if market == "HK":
                # Remove .HK suffix and leading zeros
                query_ticker = ticker.upper().replace('.HK', '').replace(' HK', '').replace(' ', '')
                query_ticker = query_ticker.lstrip('0') or '0'
                logger.debug(f"Normalized HK ticker {ticker} -> {query_ticker} for CapIQ query")

            sql = f"""
            SELECT
                c.companyid,
                c.companyname,
                c.webpage,
                ti.tickersymbol,
                ex.exchangesymbol,
                ex.exchangename,
                s.subtypevalue as industry,
                pe.pricingdate,
                pe.priceclose,
                pe.priceopen,
                pe.pricehigh,
                pe.pricelow,
                pe.volume,
                mc.marketcap
            FROM ciqcompany c
            INNER JOIN ciqsecurity sec
                ON c.companyid = sec.companyid
            INNER JOIN ciqtradingitem ti
                ON sec.securityid = ti.securityid
            INNER JOIN ciqexchange ex
                ON ti.exchangeid = ex.exchangeid
            LEFT JOIN ciqCompanyIndustryTree tree
                ON tree.companyid = c.companyid AND tree.primaryflag = 1
            LEFT JOIN ciqSubType s
                ON s.subTypeId = tree.subTypeId
            LEFT JOIN ciqpriceequity pe
                ON ti.tradingitemid = pe.tradingitemid
            LEFT JOIN ciqmarketcap mc
                ON mc.companyid = c.companyid AND mc.pricingdate = pe.pricingdate
            WHERE c.companyTypeId = 4
                AND c.companyStatusTypeId IN (1, 20)
                AND sec.primaryflag = 1
                AND UPPER(ti.tickersymbol) = UPPER(%s)
                {market_filter}
                AND pe.priceclose IS NOT NULL
            ORDER BY pe.pricingdate DESC
            LIMIT 1
            """

            cursor = self.conn.cursor()
            cursor.execute(sql, [query_ticker])
            row = cursor.fetchone()
            cursor.close()

            if not row:
                return None

            return {
                "companyid": row[0],
                "companyname": row[1],
                "webpage": row[2],
                "ticker": row[3],
                "exchange_symbol": row[4],
                "exchange_name": row[5],
                "industry": row[6],
                "pricing_date": row[7],
                "price_close": float(row[8]) if row[8] else None,
                "price_open": float(row[9]) if row[9] else None,
                "price_high": float(row[10]) if row[10] else None,
                "price_low": float(row[11]) if row[11] else None,
                "volume": int(row[12]) if row[12] else None,
                "market_cap": float(row[13]) if row[13] else None
            }
        except Exception as e:
            logger.error(f"Failed to get company data for {ticker}: {str(e)}")
            return None

    def get_hk_biotech_companies(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get Hong Kong listed biotech/pharmaceutical companies from CapIQ

        Args:
            limit: Maximum number of companies to return

        Returns:
            List of HK biotech companies with pricing data
        """
        if not self.available:
            return []

        try:
            sql = f"""
            SELECT DISTINCT
                c.companyid,
                c.companyname,
                c.webpage,
                ti.tickersymbol,
                ex.exchangesymbol,
                ex.exchangename,
                s.subtypevalue as industry,
                pe.pricingdate,
                pe.priceclose,
                pe.priceopen,
                pe.pricehigh,
                pe.pricelow,
                pe.volume,
                mc.marketcap
            FROM ciqcompany c
            INNER JOIN ciqsecurity sec
                ON c.companyid = sec.companyid
            INNER JOIN ciqtradingitem ti
                ON sec.securityid = ti.securityid
            INNER JOIN ciqexchange ex
                ON ti.exchangeid = ex.exchangeid
            LEFT JOIN ciqCompanyIndustryTree tree
                ON tree.companyid = c.companyid AND tree.primaryflag = 1
            LEFT JOIN ciqSubType s
                ON s.subTypeId = tree.subTypeId
            LEFT JOIN ciqpriceequity pe
                ON ti.tradingitemid = pe.tradingitemid
            LEFT JOIN ciqmarketcap mc
                ON mc.companyid = c.companyid AND mc.pricingdate = pe.pricingdate
            WHERE c.companyTypeId = 4
                AND c.companyStatusTypeId IN (1, 20)
                AND sec.primaryflag = 1
                AND ex.exchangename = 'The Stock Exchange of Hong Kong Ltd.'
                AND (
                    UPPER(s.subtypevalue) LIKE '%%BIOTECH%%'
                    OR UPPER(s.subtypevalue) LIKE '%%PHARMA%%'
                    OR UPPER(s.subtypevalue) LIKE '%%BIOPHARM%%'
                    OR UPPER(s.subtypevalue) LIKE '%%DRUG%%'
                    OR UPPER(c.companyname) LIKE '%%PHARMA%%'
                    OR UPPER(c.companyname) LIKE '%%BIO%%'
                )
                AND pe.priceclose IS NOT NULL
                AND pe.pricingdate = (
                    SELECT MAX(pe2.pricingdate)
                    FROM ciqpriceequity pe2
                    WHERE pe2.tradingitemid = ti.tradingitemid
                )
            ORDER BY mc.marketcap DESC NULLS LAST
            LIMIT {limit}
            """

            cursor = self.conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            cursor.close()

            results = []
            for row in rows:
                results.append({
                    "companyid": row[0],
                    "companyname": row[1],
                    "webpage": row[2],
                    "ticker": row[3],
                    "exchange_symbol": row[4],
                    "exchange_name": row[5],
                    "industry": row[6],
                    "pricing_date": row[7],
                    "price_close": float(row[8]) if row[8] else None,
                    "price_open": float(row[9]) if row[9] else None,
                    "price_high": float(row[10]) if row[10] else None,
                    "price_low": float(row[11]) if row[11] else None,
                    "volume": int(row[12]) if row[12] else None,
                    "market_cap": float(row[13]) if row[13] else None
                })

            logger.info(f"Found {len(results)} HK biotech companies from CapIQ")
            return results
        except Exception as e:
            logger.error(f"Failed to get HK biotech companies: {str(e)}")
            return []

    def get_companies_by_tickers(self, tickers: List[str], market: str = "HK") -> List[Dict[str, Any]]:
        """
        Get company data for a specific list of tickers from CapIQ
        This is more efficient than querying each ticker individually

        Args:
            tickers: List of ticker symbols (e.g., ["2561", "2552", "700"])
            market: Market identifier (US, HK, etc.)

        Returns:
            List of companies with pricing data for the matching tickers
        """
        if not self.available or not tickers:
            return []

        try:
            # Build market filter
            market_filter = ""
            if market == "US":
                market_filter = """AND (
                    ex.exchangename = 'Nasdaq Global Select'
                    OR ex.exchangename LIKE 'New York Stock Exchange%%'
                    OR ex.exchangesymbol IN ('NasdaqGS', 'NYSE', 'NYSEArca')
                )"""
            elif market == "HK":
                market_filter = "AND ex.exchangename = 'The Stock Exchange of Hong Kong Ltd.'"

            # Normalize tickers: remove .HK suffix and leading zeros for HK market
            normalized_tickers = []
            for ticker in tickers:
                ticker_clean = str(ticker).strip().upper()
                # Remove .HK suffix
                ticker_clean = ticker_clean.replace('.HK', '').replace(' HK', '').replace(' ', '')
                # Remove leading zeros for HK market (CapIQ stores as numbers)
                if market == "HK":
                    ticker_clean = ticker_clean.lstrip('0') or '0'
                normalized_tickers.append(ticker_clean)

            # Create parameterized query with IN clause
            placeholders = ','.join(['%s'] * len(normalized_tickers))

            sql = f"""
            SELECT DISTINCT
                c.companyid,
                c.companyname,
                c.webpage,
                ti.tickersymbol,
                ex.exchangesymbol,
                ex.exchangename,
                s.subtypevalue as industry,
                pe.pricingdate,
                pe.priceclose,
                pe.priceopen,
                pe.pricehigh,
                pe.pricelow,
                pe.volume,
                mc.marketcap
            FROM ciqcompany c
            INNER JOIN ciqsecurity sec
                ON c.companyid = sec.companyid
            INNER JOIN ciqtradingitem ti
                ON sec.securityid = ti.securityid
            INNER JOIN ciqexchange ex
                ON ti.exchangeid = ex.exchangeid
            LEFT JOIN ciqCompanyIndustryTree tree
                ON tree.companyid = c.companyid AND tree.primaryflag = 1
            LEFT JOIN ciqSubType s
                ON s.subTypeId = tree.subTypeId
            LEFT JOIN ciqpriceequity pe
                ON ti.tradingitemid = pe.tradingitemid
            LEFT JOIN ciqmarketcap mc
                ON mc.companyid = c.companyid AND mc.pricingdate = pe.pricingdate
            WHERE c.companyTypeId = 4
                AND c.companyStatusTypeId IN (1, 20)
                AND sec.primaryflag = 1
                AND UPPER(ti.tickersymbol) IN ({placeholders})
                {market_filter}
                AND pe.priceclose IS NOT NULL
                AND pe.pricingdate = (
                    SELECT MAX(pe2.pricingdate)
                    FROM ciqpriceequity pe2
                    WHERE pe2.tradingitemid = ti.tradingitemid
                )
            ORDER BY marketcap DESC NULLS LAST
            """

            cursor = self.conn.cursor()
            cursor.execute(sql, normalized_tickers)
            rows = cursor.fetchall()
            cursor.close()

            results = []
            companies_with_mcap = 0
            for row in rows:
                market_cap = float(row[13]) if row[13] else None
                if market_cap:
                    companies_with_mcap += 1

                results.append({
                    "companyid": row[0],
                    "companyname": row[1],
                    "webpage": row[2],
                    "ticker": row[3],
                    "exchange_symbol": row[4],
                    "exchange_name": row[5],
                    "industry": row[6],
                    "pricing_date": row[7],
                    "price_close": float(row[8]) if row[8] else None,
                    "price_open": float(row[9]) if row[9] else None,
                    "price_high": float(row[10]) if row[10] else None,
                    "price_low": float(row[11]) if row[11] else None,
                    "volume": int(row[12]) if row[12] else None,
                    "market_cap": market_cap
                })

            logger.info(f"Found {len(results)} companies from CapIQ for {len(tickers)} requested tickers ({companies_with_mcap} with market cap)")
            return results
        except Exception as e:
            logger.error(f"Failed to get companies by tickers: {str(e)}")
            return []

    def get_watchlist_companies_data(self, watchlist_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Get live CapIQ data for a list of watchlist companies

        Args:
            watchlist_items: List of watchlist items with ticker, market, exchange info

        Returns:
            List of companies with enriched CapIQ data
        """
        if not self.available:
            return []

        results = []
        for item in watchlist_items:
            try:
                # Get live CapIQ data
                company_data = self.get_company_data(
                    ticker=item['ticker'],
                    market=item.get('market', 'US'),
                    exchange_name=item.get('exchange_name')
                )

                if company_data:
                    # Merge watchlist item info with live data
                    result = {**item, **company_data}
                    results.append(result)
                else:
                    # Add watchlist item with error state
                    results.append({
                        **item,
                        "error": "Unable to fetch live data",
                        "price_close": None
                    })
            except Exception as e:
                logger.error(f"Error fetching data for {item.get('ticker')}: {str(e)}")
                results.append({
                    **item,
                    "error": str(e),
                    "price_close": None
                })

        return results

    def get_company_fundamentals(self, ticker: str, periods: int = 4) -> List[Dict[str, Any]]:
        """
        Get historical fundamentals for a company

        Args:
            ticker: Stock ticker
            periods: Number of historical periods to return

        Returns:
            List of fundamental data by period
        """
        if not self.available:
            return []

        try:
            # Template query for historical fundamentals
            sql = """
            SELECT
                f.reportdate,
                f.fiscalyear,
                f.fiscalquarter,
                f.totalrevenue,
                f.grossprofit,
                f.operatingincome,
                f.netincome,
                f.ebitda,
                f.totalassets,
                f.totaldebt,
                f.totalequity,
                f.operatingcashflow,
                f.freecashflow,
                f.capex
            FROM company_fundamentals f
            JOIN company_master c ON f.companyid = c.companyid
            WHERE c.ticker = %s
            ORDER BY f.reportdate DESC
            LIMIT %s
            """

            df = pd.read_sql(sql, self.conn, params=[ticker, periods])

            return df.to_dict('records')
        except Exception as e:
            logger.error(f"Failed to get fundamentals for {ticker}: {str(e)}")
            return []

    def get_historical_prices(self, ticker: str, market: str = "HK", days: int = 90) -> List[Dict[str, Any]]:
        """
        Get historical daily prices for a company from CapIQ

        Args:
            ticker: Stock ticker symbol (e.g., "2561.HK" or "2561")
            market: Market identifier (US, HK, etc.)
            days: Number of days of history to fetch (default 90)

        Returns:
            List of daily price records sorted by date descending
        """
        if not self.available:
            return []

        try:
            # Build market filter
            market_filter = ""
            if market == "US":
                market_filter = """AND (
                    ex.exchangename = 'Nasdaq Global Select'
                    OR ex.exchangename LIKE 'New York Stock Exchange%%'
                    OR ex.exchangesymbol IN ('NasdaqGS', 'NYSE', 'NYSEArca')
                )"""
            elif market == "HK":
                market_filter = "AND ex.exchangename = 'The Stock Exchange of Hong Kong Ltd.'"

            # Normalize ticker for HK market
            query_ticker = ticker
            if market == "HK":
                query_ticker = ticker.upper().replace('.HK', '').replace(' HK', '').replace(' ', '')
                query_ticker = query_ticker.lstrip('0') or '0'
                logger.debug(f"Normalized HK ticker {ticker} -> {query_ticker} for historical query")

            sql = f"""
            SELECT
                pe.pricingdate,
                pe.priceclose,
                pe.priceopen,
                pe.pricehigh,
                pe.pricelow,
                pe.volume
            FROM ciqcompany c
            INNER JOIN ciqsecurity sec
                ON c.companyid = sec.companyid
            INNER JOIN ciqtradingitem ti
                ON sec.securityid = ti.securityid
            INNER JOIN ciqexchange ex
                ON ti.exchangeid = ex.exchangeid
            INNER JOIN ciqpriceequity pe
                ON ti.tradingitemid = pe.tradingitemid
            WHERE c.companyTypeId = 4
                AND c.companyStatusTypeId IN (1, 20)
                AND sec.primaryflag = 1
                AND UPPER(ti.tickersymbol) = UPPER(%s)
                {market_filter}
                AND pe.priceclose IS NOT NULL
                AND pe.pricingdate >= DATEADD(day, -%s, CURRENT_DATE())
            ORDER BY pe.pricingdate DESC
            """

            cursor = self.conn.cursor()
            cursor.execute(sql, [query_ticker, days])
            rows = cursor.fetchall()
            cursor.close()

            results = []
            for row in rows:
                results.append({
                    "trade_date": row[0],
                    "close": float(row[1]) if row[1] else None,
                    "open": float(row[2]) if row[2] else None,
                    "high": float(row[3]) if row[3] else None,
                    "low": float(row[4]) if row[4] else None,
                    "volume": int(row[5]) if row[5] else None,
                })

            logger.info(f"Found {len(results)} historical price records for {ticker} from CapIQ")
            return results
        except Exception as e:
            logger.error(f"Failed to get historical prices for {ticker}: {str(e)}")
            return []

    def close(self):
        """Close Snowflake connection"""
        global _snowflake_conn
        if _snowflake_conn:
            try:
                _snowflake_conn.close()
                _snowflake_conn = None
                logger.info("Closed Snowflake CapIQ connection")
            except Exception as e:
                logger.error(f"Error closing Snowflake connection: {str(e)}")


def get_capiq_service() -> CapIQDataService:
    """Get CapIQ service instance"""
    return CapIQDataService()
