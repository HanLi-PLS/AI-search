"""
Watchlist model for tracking user's selected companies from CapIQ
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.app.database import Base


class WatchlistItem(Base):
    """
    Model for storing user watchlist items from CapIQ data
    Each row represents a company that a user is tracking
    """
    __tablename__ = "watchlist_items"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # User who owns this watchlist item
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    # Company identification from CapIQ
    company_id = Column(Integer, nullable=False)  # CapIQ companyid
    company_name = Column(String(255), nullable=False)
    ticker = Column(String(20), nullable=False)

    # Exchange information
    exchange_name = Column(String(255), nullable=False)  # Full exchange name from CapIQ
    exchange_symbol = Column(String(50), nullable=False)  # Exchange symbol (e.g., NasdaqGS, SEHK)

    # Market classification
    market = Column(String(10), nullable=False)  # US, HK, etc.

    # Additional info
    webpage = Column(String(500), nullable=True)
    industry = Column(String(255), nullable=True)

    # Metadata
    added_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationship to user (optional, for easier querying)
    # user = relationship("User", back_populates="watchlist_items")

    # Composite unique constraint: one user can only add a specific company once
    __table_args__ = (
        Index('ix_user_company', 'user_id', 'company_id', 'exchange_symbol', unique=True),
    )

    def __repr__(self):
        return f"<WatchlistItem(user_id={self.user_id}, ticker={self.ticker}, company={self.company_name})>"

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'company_id': self.company_id,
            'company_name': self.company_name,
            'ticker': self.ticker,
            'exchange_name': self.exchange_name,
            'exchange_symbol': self.exchange_symbol,
            'market': self.market,
            'webpage': self.webpage,
            'industry': self.industry,
            'added_at': self.added_at.isoformat() if self.added_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
