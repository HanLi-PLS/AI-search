"""
Custom Watchlist API endpoints - User-managed company tracking
Supports both HKEX and US markets with CapIQ data integration
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import logging
from datetime import datetime

from backend.app.models.user import User
from backend.app.models.watchlist import WatchlistItem
from backend.app.api.routes.auth import get_current_user
from backend.app.services.capiq_data import get_capiq_service
from backend.app.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


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


@router.get("/debug-schema")
async def debug_capiq_schema(
    test_ticker: str = "700",
    current_user: User = Depends(get_current_user)
):
    """
    Debug endpoint to explore CapIQ schema and find correct data item IDs

    This helps identify:
    - Available period types (to find LTM)
    - Data item IDs for revenue and IPO date
    - Sample financial data for a test company

    Args:
        test_ticker: Ticker to use for testing (default "700" = Tencent)
    """
    try:
        capiq = get_capiq_service()

        if not capiq.available:
            return {
                "success": False,
                "message": "CapIQ not available"
            }

        logger.info(f"Exploring CapIQ schema with test ticker: {test_ticker}")
        results = capiq.explore_schema_for_data_items(test_ticker)

        if "error" in results:
            return {
                "success": False,
                "error": results["error"]
            }

        return {
            "success": True,
            "test_ticker": test_ticker,
            "exploration_results": results
        }

    except Exception as e:
        logger.error(f"Schema exploration failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Schema exploration failed: {str(e)}")


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

        # Find NYSE exchange name by searching for JPMorgan Chase
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
                WHERE ti.tickersymbol = 'JPM'
                    AND c.companyTypeId = 4
                    AND c.companyStatusTypeId IN (1, 20)
                    AND sec.primaryflag = 1
                LIMIT 5
            """)
            jpm_results = cursor.fetchall()
            results["jpm_exchange"] = [
                {
                    "company": row[0],
                    "ticker": row[1],
                    "exchange": row[2],
                    "exchange_symbol": row[3],
                    "primary_flag": row[4]
                }
                for row in jpm_results
            ]
        except Exception as e:
            results["jpm_error"] = str(e)

        cursor.close()
        return {"success": True, "results": results}

    except Exception as e:
        logger.error(f"Debug query failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test-apple-filter")
async def test_apple_filter(current_user: User = Depends(get_current_user)):
    """
    Test the exact filter conditions used in search to debug Apple issue
    """
    try:
        capiq = get_capiq_service()
        if not capiq.available:
            return {"success": False, "message": "CapIQ not available"}

        cursor = capiq.conn.cursor()
        results = {}

        # Test the EXACT query used in search_companies() for Apple
        try:
            sql = """
            SELECT DISTINCT
                c.companyid,
                c.companyname,
                c.webpage,
                ti.tickersymbol,
                ex.exchangesymbol,
                ex.exchangename,
                s.subtypevalue as industry,
                sec.primaryflag,
                c.companyTypeId,
                c.companyStatusTypeId
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
            WHERE c.companyTypeId = 4
                AND c.companyStatusTypeId IN (1, 20)
                AND sec.primaryflag = 1
                AND (UPPER(c.companyname) LIKE UPPER(%s) OR UPPER(ti.tickersymbol) LIKE UPPER(%s))
                AND (
                    ex.exchangename = 'Nasdaq Global Select'
                    OR ex.exchangename LIKE 'New York Stock Exchange%%'
                    OR ex.exchangesymbol IN ('NasdaqGS', 'NYSE', 'NYSEArca')
                )
            LIMIT 10
            """
            cursor.execute(sql, ['%Apple%', '%Apple%'])
            apple_results = cursor.fetchall()
            results["apple_with_filter"] = [
                {
                    "companyid": row[0],
                    "companyname": row[1],
                    "webpage": row[2],
                    "ticker": row[3],
                    "exchange_symbol": row[4],
                    "exchange_name": row[5],
                    "industry": row[6],
                    "primary_flag": row[7],
                    "company_type": row[8],
                    "company_status": row[9]
                }
                for row in apple_results
            ]
        except Exception as e:
            results["apple_with_filter_error"] = str(e)

        # Test without primaryflag filter
        try:
            sql = """
            SELECT DISTINCT
                c.companyid,
                c.companyname,
                ti.tickersymbol,
                ex.exchangesymbol,
                ex.exchangename,
                sec.primaryflag
            FROM ciqcompany c
            INNER JOIN ciqsecurity sec ON c.companyid = sec.companyid
            INNER JOIN ciqtradingitem ti ON sec.securityid = ti.securityid
            INNER JOIN ciqexchange ex ON ti.exchangeid = ex.exchangeid
            WHERE c.companyTypeId = 4
                AND c.companyStatusTypeId IN (1, 20)
                AND (UPPER(c.companyname) LIKE UPPER(%s) OR UPPER(ti.tickersymbol) LIKE UPPER(%s))
                AND (
                    ex.exchangename = 'Nasdaq Global Select'
                    OR ex.exchangename LIKE 'New York Stock Exchange%%'
                    OR ex.exchangesymbol IN ('NasdaqGS', 'NYSE', 'NYSEArca')
                )
            LIMIT 10
            """
            cursor.execute(sql, ['%Apple%', '%Apple%'])
            apple_no_primary = cursor.fetchall()
            results["apple_without_primaryflag"] = [
                {
                    "companyid": row[0],
                    "companyname": row[1],
                    "ticker": row[2],
                    "exchange_symbol": row[3],
                    "exchange_name": row[4],
                    "primary_flag": row[5]
                }
                for row in apple_no_primary
            ]
        except Exception as e:
            results["apple_without_primaryflag_error"] = str(e)

        cursor.close()
        return {"success": True, "results": results}

    except Exception as e:
        logger.error(f"Apple filter test failed: {str(e)}")
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add a company to user's watchlist

    Args:
        ticker: Stock ticker symbol
        market: Market identifier (US, HK, etc.)

    Returns company data from CapIQ and stores in database
    """
    try:
        # Get company data from CapIQ first to ensure it exists
        capiq = get_capiq_service()

        if not capiq.available:
            raise HTTPException(status_code=503, detail="CapIQ service not available")

        company_data = capiq.get_company_data(ticker, market)

        if not company_data:
            raise HTTPException(
                status_code=404,
                detail=f"Company with ticker {ticker} not found in {market} market"
            )

        # Check if already in watchlist
        existing = db.query(WatchlistItem).filter(
            WatchlistItem.user_id == current_user.id,
            WatchlistItem.company_id == company_data['companyid'],
            WatchlistItem.exchange_symbol == company_data['exchange_symbol']
        ).first()

        if existing:
            return {
                "success": False,
                "message": f"{company_data['companyname']} ({ticker}) already in watchlist",
                "company": existing.to_dict()
            }

        # Create new watchlist item
        watchlist_item = WatchlistItem(
            user_id=current_user.id,
            company_id=company_data['companyid'],
            company_name=company_data['companyname'],
            ticker=ticker.upper(),
            exchange_name=company_data['exchange_name'],
            exchange_symbol=company_data['exchange_symbol'],
            market=market,
            webpage=company_data.get('webpage'),
            industry=company_data.get('industry')
        )

        db.add(watchlist_item)
        db.commit()
        db.refresh(watchlist_item)

        return {
            "success": True,
            "message": f"Added {company_data['companyname']} ({ticker}) to watchlist",
            "company": watchlist_item.to_dict(),
            "live_data": company_data
        }

    except HTTPException:
        raise
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Duplicate watchlist item for user {current_user.id}, ticker {ticker}: {str(e)}")
        raise HTTPException(status_code=409, detail=f"{ticker} already in watchlist")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to add {ticker} to watchlist: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to add to watchlist: {str(e)}")


@router.delete("/remove")
async def remove_from_watchlist(
    ticker: str,
    market: str = "US",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Remove a company from user's watchlist

    Args:
        ticker: Stock ticker symbol
        market: Market identifier (US, HK, etc.)
    """
    try:
        # Find the watchlist item(s) matching ticker and market
        watchlist_items = db.query(WatchlistItem).filter(
            WatchlistItem.user_id == current_user.id,
            WatchlistItem.ticker == ticker.upper(),
            WatchlistItem.market == market
        ).all()

        if not watchlist_items:
            return {
                "success": False,
                "message": f"{ticker} ({market}) not found in watchlist"
            }

        # Delete all matching items
        for item in watchlist_items:
            db.delete(item)

        db.commit()

        return {
            "success": True,
            "message": f"Removed {ticker} ({market}) from watchlist",
            "removed_count": len(watchlist_items)
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to remove {ticker} from watchlist: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to remove from watchlist: {str(e)}")


@router.get("/list")
async def get_watchlist(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get user's watchlist with latest live data from CapIQ

    Returns stored watchlist items enriched with real-time pricing data
    """
    try:
        # Get user's watchlist items from database
        watchlist_items = db.query(WatchlistItem).filter(
            WatchlistItem.user_id == current_user.id
        ).order_by(WatchlistItem.added_at.desc()).all()

        if not watchlist_items:
            return {
                "success": True,
                "count": 0,
                "companies": []
            }

        # Enrich with live data from CapIQ
        capiq = get_capiq_service()
        companies = []

        for item in watchlist_items:
            company_dict = item.to_dict()

            # Try to get live data from CapIQ
            if capiq and capiq.available:
                try:
                    live_data = capiq.get_company_data(
                        item.ticker,
                        item.market,
                        exchange_name=item.exchange_name
                    )
                    if live_data:
                        # Calculate intraday change from CapIQ open/close prices
                        change = None
                        change_percent = None
                        if live_data.get('price_close') and live_data.get('price_open'):
                            change = live_data['price_close'] - live_data['price_open']
                            change_percent = (change / live_data['price_open'] * 100) if live_data['price_open'] != 0 else 0

                        # Merge stored data with live data
                        company_dict['live_data'] = {
                            'price_close': live_data.get('price_close'),
                            'price_open': live_data.get('price_open'),
                            'price_high': live_data.get('price_high'),
                            'price_low': live_data.get('price_low'),
                            'volume': live_data.get('volume'),
                            'market_cap': live_data.get('market_cap'),
                            'market_cap_currency': live_data.get('market_cap_currency'),
                            'pricing_date': live_data.get('pricing_date'),
                            'ttm_revenue': live_data.get('ttm_revenue'),
                            'ttm_revenue_currency': live_data.get('ttm_revenue_currency'),
                            'ttm_revenue_converted': live_data.get('ttm_revenue_converted'),
                            'exchange_rate_used': live_data.get('exchange_rate_used'),
                            'ps_ratio': live_data.get('ps_ratio'),
                            'ps_ratio_note': live_data.get('ps_ratio_note'),
                            'listing_date': live_data.get('listing_date'),
                            'change': change,
                            'change_percent': change_percent,
                        }
                        company_dict['data_available'] = True
                    else:
                        company_dict['data_available'] = False
                except Exception as e:
                    logger.warning(f"Failed to fetch live data for {item.ticker}: {str(e)}")
                    company_dict['data_available'] = False
            else:
                company_dict['data_available'] = False

            companies.append(company_dict)

        return {
            "success": True,
            "count": len(companies),
            "companies": companies,
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

    Includes current pricing data and company information.
    Historical fundamentals will be added in future updates.
    """
    try:
        capiq = get_capiq_service()

        if not capiq.available:
            raise HTTPException(
                status_code=503,
                detail="CapIQ service not available"
            )

        # Get current company data with pricing
        company_data = capiq.get_company_data(ticker, market)

        if not company_data:
            raise HTTPException(
                status_code=404,
                detail=f"Company {ticker} ({market}) not found in CapIQ"
            )

        # Try to get historical fundamentals (optional - may not be available yet)
        fundamentals = []
        try:
            fundamentals = capiq.get_company_fundamentals(ticker, periods=8)
        except Exception as e:
            logger.warning(f"Fundamentals not available for {ticker}: {str(e)}")

        return {
            "success": True,
            "ticker": ticker,
            "market": market,
            "company": company_data,
            "fundamentals": fundamentals,
            "fundamental_periods": len(fundamentals)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get company details for {ticker}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get company details: {str(e)}")
