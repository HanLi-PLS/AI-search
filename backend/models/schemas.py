from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class BiotechCompany(BaseModel):
    """Model for a biotech company"""
    name: str
    ticker: str
    sector: str


class StockPrice(BaseModel):
    """Model for stock price data"""
    ticker: str
    name: str
    current_price: Optional[float] = None
    previous_close: Optional[float] = None
    open: Optional[float] = None
    day_high: Optional[float] = None
    day_low: Optional[float] = None
    volume: Optional[int] = None
    market_cap: Optional[float] = None
    change: Optional[float] = None
    change_percent: Optional[float] = None
    currency: Optional[str] = "HKD"
    last_updated: Optional[str] = None
    error: Optional[str] = None


class IPOCompany(BaseModel):
    """Model for upcoming IPO company"""
    name: str
    expected_listing_date: Optional[str] = None
    sector: str
    description: Optional[str] = None
    status: str  # "upcoming", "pending", "listed"
