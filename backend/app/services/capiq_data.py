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
    Returns None if CapIQ is not configured
    """
    global _snowflake_conn

    if not settings.USE_CAPIQ_DATA:
        return None

    if _snowflake_conn is None:
        try:
            import snowflake.connector

            _snowflake_conn = snowflake.connector.connect(
                user=settings.SNOWFLAKE_USER,
                password=settings.SNOWFLAKE_PASSWORD,
                account=settings.SNOWFLAKE_ACCOUNT,
                warehouse=settings.SNOWFLAKE_WAREHOUSE,
                database=settings.SNOWFLAKE_DATABASE,
                schema=settings.SNOWFLAKE_SCHEMA
            )
            logger.info(f"Connected to Snowflake CapIQ: {settings.SNOWFLAKE_DATABASE}.{settings.SNOWFLAKE_SCHEMA}")
        except ImportError:
            logger.error("snowflake-connector-python not installed. Install with: pip install snowflake-connector-python")
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
            Dict with connection status and available tables
        """
        if not self.available:
            return {
                "success": False,
                "message": "CapIQ not configured or connection failed",
                "configured": settings.USE_CAPIQ_DATA
            }

        try:
            # Test query to list available tables
            query = """
            SHOW TABLES IN SCHEMA
            """
            cursor = self.conn.cursor()
            cursor.execute(query)
            tables = cursor.fetchall()
            cursor.close()

            table_names = [row[1] for row in tables]  # Table name is in second column

            return {
                "success": True,
                "message": f"Connected to {settings.SNOWFLAKE_DATABASE}.{settings.SNOWFLAKE_SCHEMA}",
                "tables": table_names,
                "table_count": len(table_names)
            }
        except Exception as e:
            logger.error(f"CapIQ connection test failed: {str(e)}")
            return {
                "success": False,
                "message": f"Connection test failed: {str(e)}"
            }

    def search_companies(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for companies by name or ticker

        Args:
            query: Search query (company name or ticker)
            limit: Maximum number of results

        Returns:
            List of matching companies with basic info
        """
        if not self.available:
            return []

        try:
            # This is a template query - adjust based on your actual CapIQ schema
            sql = """
            SELECT
                companyid,
                companyname,
                ticker,
                exchange,
                country,
                marketcap
            FROM company_master
            WHERE UPPER(companyname) LIKE UPPER(%s)
               OR UPPER(ticker) LIKE UPPER(%s)
            LIMIT %s
            """

            search_pattern = f"%{query}%"
            df = pd.read_sql(sql, self.conn, params=[search_pattern, search_pattern, limit])

            return df.to_dict('records')
        except Exception as e:
            logger.error(f"Company search failed: {str(e)}")
            return []

    def get_company_data(self, ticker: str, market: str = "US") -> Optional[Dict[str, Any]]:
        """
        Get comprehensive company data from CapIQ

        Args:
            ticker: Stock ticker symbol
            market: Market identifier (US, HK, etc.)

        Returns:
            Company data dictionary or None if not found
        """
        if not self.available:
            return None

        try:
            # Template query - adjust to match your CapIQ schema
            # This query should be customized based on the actual tables and columns available
            sql = """
            SELECT
                c.companyid,
                c.companyname AS name,
                c.ticker,
                c.exchange,
                c.country,
                c.sector,
                c.industry,
                f.marketcap AS market_cap,
                f.totalrevenue AS revenue,
                f.netincome AS net_income,
                f.totalassets AS total_assets,
                f.totaldebt AS total_debt,
                f.totalequity AS total_equity,
                f.operatingcashflow AS operating_cash_flow,
                f.capex,
                p.price AS current_price,
                p.pe_ratio,
                p.pb_ratio,
                p.ps_ratio,
                p.ev_ebitda,
                p.dividend_yield
            FROM company_master c
            LEFT JOIN company_fundamentals f ON c.companyid = f.companyid
            LEFT JOIN company_pricing p ON c.companyid = p.companyid
            WHERE c.ticker = %s
              AND c.exchange LIKE %s
            ORDER BY f.reportdate DESC
            LIMIT 1
            """

            # Adjust exchange pattern based on market
            exchange_pattern = "%HK%" if market == "HK" else "%"

            df = pd.read_sql(sql, self.conn, params=[ticker, exchange_pattern])

            if df.empty:
                return None

            return df.iloc[0].to_dict()
        except Exception as e:
            logger.error(f"Failed to get company data for {ticker}: {str(e)}")
            return None

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
