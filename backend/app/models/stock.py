"""
Stock data models for storing historical price data
"""
from sqlalchemy import Column, String, Float, Integer, Date, DateTime, Index
from sqlalchemy.sql import func
from datetime import datetime
from backend.app.database import Base


class StockDaily(Base):
    """
    Model for storing daily stock price data from Tushare
    """
    __tablename__ = "stock_daily"

    # Primary key: combination of ticker and trade_date
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Stock identification
    ticker = Column(String(20), nullable=False, index=True)  # e.g., "1801.HK"
    ts_code = Column(String(20), nullable=False, index=True)  # e.g., "01801.HK" (Tushare format)
    trade_date = Column(Date, nullable=False, index=True)  # Trading date

    # OHLCV data
    open = Column(Float, nullable=True)
    high = Column(Float, nullable=True)
    low = Column(Float, nullable=True)
    close = Column(Float, nullable=False)  # Close price is essential
    pre_close = Column(Float, nullable=True)

    # Volume and amount
    volume = Column(Float, nullable=True)  # Trading volume (shares)
    amount = Column(Float, nullable=True)  # Trading amount (HKD)

    # Change metrics
    change = Column(Float, nullable=True)  # Price change
    pct_change = Column(Float, nullable=True)  # Percentage change

    # Metadata
    data_source = Column(String(50), default="Tushare Pro")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Composite index for efficient queries
    __table_args__ = (
        Index('ix_ticker_trade_date', 'ticker', 'trade_date', unique=True),
    )

    def __repr__(self):
        return f"<StockDaily(ticker={self.ticker}, date={self.trade_date}, close={self.close})>"

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'ticker': self.ticker,
            'ts_code': self.ts_code,
            'trade_date': self.trade_date.isoformat() if self.trade_date else None,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'pre_close': self.pre_close,
            'volume': self.volume,
            'amount': self.amount,
            'change': self.change,
            'pct_change': self.pct_change,
            'data_source': self.data_source,
        }
