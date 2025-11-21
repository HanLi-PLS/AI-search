"""
Custom Watchlist API endpoints - User-managed company tracking
Supports both HKEX and US markets with CapIQ data integration
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from backend.app.models.user import User
from backend.app.api.routes.auth import get_current_user
from backend.app.services.capiq_data import get_capiq_service

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory watchlist storage (per user)
# In production, this should be stored in database
_user_watchlists: Dict[str, List[Dict[str, Any]]] = {}


@router.post("/test-capiq")
async def test_capiq_connection(current_user: User = Depends(get_current_user)):
    """
    Test CapIQ/Snowflake connection

    Returns connection status and available tables
    """
    try:
        capiq = get_capiq_service()
        result = capiq.test_connection()

        return {
            "success": result.get("success", False),
            "message": result.get("message", ""),
            "details": {
                "configured": result.get("configured", False),
                "tables": result.get("tables", []),
                "views": result.get("views", []),
                "all_objects": result.get("all_objects", []),
                "table_count": result.get("table_count", 0),
                "view_count": result.get("view_count", 0),
                "total_count": result.get("total_count", 0)
            }
        }
    except Exception as e:
        logger.error(f"CapIQ connection test failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Connection test failed: {str(e)}")


@router.get("/debug-exchanges")
async def debug_exchanges(current_user: User = Depends(get_current_user)):
    """
    Debug endpoint to find US exchanges and search for Apple
    """
    try:
        capiq = get_capiq_service()
        if not capiq.available:
            return {"success": False, "message": "CapIQ not available"}

        cursor = capiq.conn.cursor()
        results = {}

        # Find US exchanges
        try:
            cursor.execute("""
                SELECT DISTINCT ex.exchangename
                FROM ciqexchange ex
                WHERE ex.exchangename LIKE '%New York%'
                   OR ex.exchangename LIKE '%Nasdaq%'
                   OR ex.exchangename LIKE '%NYSE%'
                LIMIT 20
            """)
            us_exchanges = [row[0] for row in cursor.fetchall()]
            results["us_exchanges"] = us_exchanges
        except Exception as e:
            results["us_exchanges_error"] = str(e)

        # Search for Apple WITHOUT market filter
        try:
            cursor.execute("""
                SELECT DISTINCT
                    c.companyname,
                    ti.tickersymbol,
                    ex.exchangename,
                    c.companyTypeId,
                    c.companyStatusTypeId,
                    sec.primaryflag
                FROM ciqcompany c
                INNER JOIN ciqsecurity sec ON c.companyid = sec.companyid
                INNER JOIN ciqtradingitem ti ON sec.securityid = ti.securityid
                INNER JOIN ciqexchange ex ON ti.exchangeid = ex.exchangeid
                WHERE UPPER(c.companyname) LIKE '%APPLE%'
                LIMIT 10
            """)
            apple_all = cursor.fetchall()
            results["apple_all_results"] = [
                {
                    "company": row[0],
                    "ticker": row[1],
                    "exchange": row[2],
                    "type_id": row[3],
                    "status_id": row[4],
                    "primary_flag": row[5]
                }
                for row in apple_all
            ]
        except Exception as e:
            results["apple_all_error"] = str(e)

        # Search with AAPL ticker - exact match
        try:
            cursor.execute("""
                SELECT DISTINCT
                    c.companyname,
                    ti.tickersymbol,
                    ex.exchangename,
                    ex.exchangesymbol,
                    sec.primaryflag
                FROM ciqcompany c
                INNER JOIN ciqsecurity sec ON c.companyid = sec.companyid
                INNER JOIN ciqtradingitem ti ON sec.securityid = ti.securityid
                INNER JOIN ciqexchange ex ON ti.exchangeid = ex.exchangeid
                WHERE ti.tickersymbol = 'AAPL'
                    AND c.companyTypeId = 4
                    AND c.companyStatusTypeId IN (1, 20)
                LIMIT 20
            """)
            aapl_exact = cursor.fetchall()
            results["aapl_exact_match"] = [
                {
                    "company": row[0],
                    "ticker": row[1],
                    "exchange": row[2],
                    "exchange_symbol": row[3],
                    "primary_flag": row[4]
                }
                for row in aapl_exact
            ]
        except Exception as e:
            results["aapl_exact_error"] = str(e)

        # Find all exchanges with "Global Select" or just contains ticker AAPL
        try:
            cursor.execute("""
                SELECT DISTINCT ex.exchangename
                FROM ciqexchange ex
                WHERE ex.exchangename LIKE '%Global%'
                   OR ex.exchangename LIKE '%Select%'
                   OR ex.exchangename LIKE '%Stock Market%'
                LIMIT 20
            """)
            global_exchanges = [row[0] for row in cursor.fetchall()]
            results["global_select_exchanges"] = global_exchanges
        except Exception as e:
            results["global_exchanges_error"] = str(e)

        cursor.close()
        return {"success": True, "results": results}

    except Exception as e:
        logger.error(f"Debug query failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test-query")
async def test_query_capiq(current_user: User = Depends(get_current_user)):
    """
    Test querying CapIQ views to explore data structure

    Queries sample data from key CapIQ views to understand what's available
    """
    try:
        capiq = get_capiq_service()

        if not capiq.available:
            return {
                "success": False,
                "message": "CapIQ not available"
            }

        cursor = capiq.conn.cursor()
        results = {}

        # Test 1: Sample companies (discover columns with SELECT *)
        try:
            cursor.execute("""
                SELECT *
                FROM CIQCOMPANY
                LIMIT 2
            """)
            companies = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            results["sample_companies"] = {
                "columns": column_names[:15],  # First 15 column names
                "row_count": len(companies),
                "sample_data": [dict(zip(column_names[:15], row[:15])) for row in companies]
            }
        except Exception as e:
            results["sample_companies_error"] = str(e)

        # Test 2: Sample securities (discover columns)
        try:
            cursor.execute("""
                SELECT *
                FROM CIQSECURITY
                LIMIT 2
            """)
            securities = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            results["sample_securities"] = {
                "columns": column_names[:15],  # First 15 column names
                "row_count": len(securities),
                "sample_data": [dict(zip(column_names[:15], row[:15])) for row in securities]
            }
        except Exception as e:
            results["sample_securities_error"] = str(e)

        # Test 3: Sample trading items (tickers)
        try:
            cursor.execute("""
                SELECT
                    tradingitemid,
                    securityid,
                    tickersymbol,
                    exchangeid
                FROM CIQTRADINGITEM
                WHERE tickersymbol IS NOT NULL
                LIMIT 5
            """)
            trading_items = cursor.fetchall()
            results["sample_trading_items"] = [
                {
                    "tradingitemid": row[0],
                    "securityid": row[1],
                    "tickersymbol": row[2],
                    "exchangeid": row[3]
                }
                for row in trading_items
            ]
        except Exception as e:
            results["sample_trading_items_error"] = str(e)

        cursor.close()

        return {
            "success": True,
            "message": "Test queries executed",
            "results": results
        }

    except Exception as e:
        logger.error(f"Test query failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Test query failed: {str(e)}")


@router.get("/search")
async def search_companies(
    query: str,
    limit: int = 10,
    market: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Search for companies by name or ticker across all markets

    Args:
        query: Company name or ticker to search for
        limit: Maximum number of results (default 10)
        market: Optional market filter ('US', 'HK', or None for all markets)

    Uses CapIQ if available, otherwise returns empty results
    """
    try:
        capiq = get_capiq_service()

        if not capiq.available:
            return {
                "success": False,
                "message": "CapIQ not configured. Please configure Snowflake credentials.",
                "companies": []
            }

        companies = capiq.search_companies(query, limit, market)

        return {
            "success": True,
            "query": query,
            "market_filter": market,
            "count": len(companies),
            "companies": companies
        }
    except Exception as e:
        logger.error(f"Company search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/add")
async def add_to_watchlist(
    ticker: str,
    market: str = "US",
    current_user: User = Depends(get_current_user)
):
    """
    Add a company to user's watchlist

    Args:
        ticker: Stock ticker symbol
        market: Market identifier (US, HK, etc.)
    """
    try:
        user_id = current_user.email

        # Initialize user watchlist if not exists
        if user_id not in _user_watchlists:
            _user_watchlists[user_id] = []

        # Check if already in watchlist
        existing = [c for c in _user_watchlists[user_id] if c['ticker'] == ticker and c['market'] == market]
        if existing:
            return {
                "success": False,
                "message": f"{ticker} ({market}) already in watchlist"
            }

        # Get company data from CapIQ
        capiq = get_capiq_service()
        company_data = None

        if capiq.available:
            company_data = capiq.get_company_data(ticker, market)

        # Add to watchlist
        watchlist_item = {
            "ticker": ticker,
            "market": market,
            "added_at": datetime.now().isoformat(),
            "data": company_data
        }

        _user_watchlists[user_id].append(watchlist_item)

        return {
            "success": True,
            "message": f"Added {ticker} ({market}) to watchlist",
            "company": watchlist_item
        }
    except Exception as e:
        logger.error(f"Failed to add {ticker} to watchlist: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to add to watchlist: {str(e)}")


@router.delete("/remove")
async def remove_from_watchlist(
    ticker: str,
    market: str = "US",
    current_user: User = Depends(get_current_user)
):
    """
    Remove a company from user's watchlist
    """
    try:
        user_id = current_user.email

        if user_id not in _user_watchlists:
            return {
                "success": False,
                "message": "Watchlist is empty"
            }

        # Remove from watchlist
        original_len = len(_user_watchlists[user_id])
        _user_watchlists[user_id] = [
            c for c in _user_watchlists[user_id]
            if not (c['ticker'] == ticker and c['market'] == market)
        ]

        removed = original_len > len(_user_watchlists[user_id])

        if removed:
            return {
                "success": True,
                "message": f"Removed {ticker} ({market}) from watchlist"
            }
        else:
            return {
                "success": False,
                "message": f"{ticker} ({market}) not found in watchlist"
            }
    except Exception as e:
        logger.error(f"Failed to remove {ticker} from watchlist: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to remove from watchlist: {str(e)}")


@router.get("/list")
async def get_watchlist(current_user: User = Depends(get_current_user)):
    """
    Get user's watchlist with latest data

    Refreshes company data from CapIQ if available
    """
    try:
        user_id = current_user.email

        if user_id not in _user_watchlists or not _user_watchlists[user_id]:
            return {
                "success": True,
                "count": 0,
                "companies": []
            }

        watchlist = _user_watchlists[user_id]

        # Refresh data from CapIQ if available
        capiq = get_capiq_service()
        if capiq.available:
            for item in watchlist:
                try:
                    updated_data = capiq.get_company_data(item['ticker'], item['market'])
                    if updated_data:
                        item['data'] = updated_data
                        item['last_updated'] = datetime.now().isoformat()
                except Exception as e:
                    logger.warning(f"Failed to refresh data for {item['ticker']}: {str(e)}")

        return {
            "success": True,
            "count": len(watchlist),
            "companies": watchlist,
            "capiq_available": capiq.available if capiq else False
        }
    except Exception as e:
        logger.error(f"Failed to get watchlist: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get watchlist: {str(e)}")


@router.get("/company/{ticker}")
async def get_company_details(
    ticker: str,
    market: str = "US",
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed company information from CapIQ

    Includes fundamentals, pricing, and historical data
    """
    try:
        capiq = get_capiq_service()

        if not capiq.available:
            return {
                "success": False,
                "message": "CapIQ not configured"
            }

        # Get current data
        company_data = capiq.get_company_data(ticker, market)

        if not company_data:
            return {
                "success": False,
                "message": f"Company {ticker} ({market}) not found in CapIQ"
            }

        # Get historical fundamentals
        fundamentals = capiq.get_company_fundamentals(ticker, periods=8)

        return {
            "success": True,
            "ticker": ticker,
            "market": market,
            "data": company_data,
            "fundamentals": fundamentals,
            "fundamental_periods": len(fundamentals)
        }
    except Exception as e:
        logger.error(f"Failed to get company details for {ticker}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get company details: {str(e)}")
