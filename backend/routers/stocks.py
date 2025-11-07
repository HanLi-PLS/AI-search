from fastapi import APIRouter, HTTPException, Query
from typing import List
from ..models.schemas import BiotechCompany, StockPrice, IPOCompany
from ..services.stock_service import StockService

router = APIRouter(prefix="/api/stocks", tags=["stocks"])

# Initialize stock service
stock_service = StockService()


@router.get("/companies", response_model=List[BiotechCompany])
async def get_biotech_companies():
    """
    Get list of all HKEX 18A biotech companies
    """
    try:
        return stock_service.get_biotech_companies()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prices", response_model=List[StockPrice])
async def get_all_stock_prices():
    """
    Get current stock prices for all biotech companies
    """
    try:
        return stock_service.get_all_stock_prices()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/price/{ticker}", response_model=StockPrice)
async def get_stock_price(ticker: str):
    """
    Get current stock price for a specific ticker

    Args:
        ticker: Stock ticker symbol (e.g., "1801.HK")
    """
    try:
        # Find company name
        companies = stock_service.get_biotech_companies()
        company = next((c for c in companies if c.ticker == ticker), None)

        if not company:
            raise HTTPException(status_code=404, detail=f"Company with ticker {ticker} not found")

        return stock_service.get_stock_price(ticker, company.name)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{ticker}")
async def get_stock_history(
    ticker: str,
    period: str = Query(default="1mo", regex="^(1d|5d|1mo|3mo|6mo|1y|2y|5y|10y|ytd|max)$")
):
    """
    Get historical stock data for a ticker

    Args:
        ticker: Stock ticker symbol (e.g., "1801.HK")
        period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
    """
    try:
        return stock_service.get_stock_history(ticker, period)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/upcoming-ipos", response_model=List[IPOCompany])
async def get_upcoming_ipos():
    """
    Get list of upcoming biotech IPOs

    Note: This is placeholder data. Integration with HKEX API needed for real data.
    """
    try:
        return stock_service.get_upcoming_ipos()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
