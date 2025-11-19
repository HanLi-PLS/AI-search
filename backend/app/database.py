"""
Database configuration for AI Search application
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from pathlib import Path

# Database file location - use relative path to project root
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATABASE_DIR = BASE_DIR / "data" / "db"
DATABASE_URL = f"sqlite:///{DATABASE_DIR}/stocks.db"

# Defer directory creation until engine is actually used
def ensure_db_directory():
    """Create database directory if it doesn't exist"""
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)

# Create SQLAlchemy engine
engine = None

def get_engine():
    """Get or create database engine"""
    global engine
    if engine is None:
        ensure_db_directory()
        engine = create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False},  # Needed for SQLite
            echo=False  # Set to True for SQL query logging
        )
    return engine

# Create SessionLocal class
SessionLocal = None

def get_session_local():
    """Get or create SessionLocal"""
    global SessionLocal
    if SessionLocal is None:
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return SessionLocal


# Create Base class for models
Base = declarative_base()


def get_db():
    """
    Dependency for getting database session
    Usage in FastAPI: db: Session = Depends(get_db)
    """
    session_local = get_session_local()
    db = session_local()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database - create all tables
    """
    from backend.app.models.stock import StockDaily  # Import models
    from backend.app.models.user import User  # Import User model
    ensure_db_directory()
    engine_instance = get_engine()
    Base.metadata.create_all(bind=engine_instance)
