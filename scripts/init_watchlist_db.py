#!/usr/bin/env python3
"""
Initialize watchlist database table

This script creates the watchlist_items table in the database.
Run this once after deploying the watchlist feature.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.database import init_db

if __name__ == "__main__":
    print("Initializing database tables...")
    try:
        init_db()
        print("✓ Database tables created successfully!")
        print("  - users")
        print("  - stock_daily")
        print("  - watchlist_items (NEW)")
    except Exception as e:
        print(f"✗ Error initializing database: {e}")
        sys.exit(1)
