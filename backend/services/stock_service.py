import yfinance as yf
import json
import os
from typing import List, Optional
from datetime import datetime
from pathlib import Path
from ..models.schemas import BiotechCompany, StockPrice, IPOCompany


class StockService:
    """Service for fetching HKEX biotech stock data"""

    def __init__(self):
        # Load the biotech companies data
        data_file = Path(__file__).parent.parent / "data" / "hkex_18a_biotech_companies.json"
        with open(data_file, 'r') as f:
            self.companies_data = json.load(f)

    def get_biotech_companies(self) -> List[BiotechCompany]:
        """Get list of all HKEX 18A biotech companies"""
        return [BiotechCompany(**company) for company in self.companies_data]

    def get_stock_price(self, ticker: str, company_name: str) -> StockPrice:
        """
        Get current stock price for a ticker

        Args:
            ticker: Stock ticker symbol (e.g., "1801.HK")
            company_name: Company name

        Returns:
            StockPrice object with current price data
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            # Get current price from various possible fields
            current_price = (
                info.get('currentPrice') or
                info.get('regularMarketPrice') or
                info.get('previousClose')
            )

            previous_close = info.get('previousClose')

            # Calculate change
            change = None
            change_percent = None
            if current_price and previous_close:
                change = current_price - previous_close
                change_percent = (change / previous_close) * 100

            return StockPrice(
                ticker=ticker,
                name=company_name,
                current_price=current_price,
                previous_close=previous_close,
                open=info.get('open') or info.get('regularMarketOpen'),
                day_high=info.get('dayHigh') or info.get('regularMarketDayHigh'),
                day_low=info.get('dayLow') or info.get('regularMarketDayLow'),
                volume=info.get('volume') or info.get('regularMarketVolume'),
                market_cap=info.get('marketCap'),
                change=change,
                change_percent=change_percent,
                currency=info.get('currency', 'HKD'),
                last_updated=datetime.now().isoformat()
            )
        except Exception as e:
            return StockPrice(
                ticker=ticker,
                name=company_name,
                error=str(e),
                last_updated=datetime.now().isoformat()
            )

    def get_all_stock_prices(self) -> List[StockPrice]:
        """Get current prices for all biotech companies"""
        companies = self.get_biotech_companies()
        stock_prices = []

        for company in companies:
            price_data = self.get_stock_price(company.ticker, company.name)
            stock_prices.append(price_data)

        return stock_prices

    def get_upcoming_ipos(self) -> List[IPOCompany]:
        """
        Get list of upcoming biotech IPOs

        Note: This is a placeholder. In production, you would integrate with
        HKEX API or other data sources for real IPO information.
        """
        # Placeholder data - replace with actual API integration
        upcoming_ipos = [
            IPOCompany(
                name="Example Biotech Co. (Placeholder)",
                expected_listing_date="TBD",
                sector="Biotech",
                description="This is placeholder data. Integrate with HKEX API for real IPO information.",
                status="upcoming"
            )
        ]

        return upcoming_ipos

    def get_stock_history(self, ticker: str, period: str = "1mo") -> dict:
        """
        Get historical stock data

        Args:
            ticker: Stock ticker symbol
            period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)

        Returns:
            Dictionary with historical price data
        """
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period=period)

            # Convert DataFrame to dict with date strings as keys
            history_data = {
                "ticker": ticker,
                "period": period,
                "data": [
                    {
                        "date": date.strftime("%Y-%m-%d"),
                        "open": row['Open'],
                        "high": row['High'],
                        "low": row['Low'],
                        "close": row['Close'],
                        "volume": int(row['Volume'])
                    }
                    for date, row in hist.iterrows()
                ]
            }

            return history_data
        except Exception as e:
            return {
                "ticker": ticker,
                "period": period,
                "error": str(e)
            }
