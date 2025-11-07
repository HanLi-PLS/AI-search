# HKEX Biotech Stock Tracker - Backend

FastAPI backend for tracking HKEX 18A biotech company stock prices and upcoming IPOs.

## Features

- Fetch real-time stock prices for HKEX 18A biotech companies using yfinance
- Get list of all tracked biotech companies
- Retrieve historical stock data
- Track upcoming IPOs (placeholder - needs HKEX API integration)

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the server:
```bash
# From the backend directory
uvicorn main:app --reload

# Or from the project root
uvicorn backend.main:app --reload
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Endpoints

### Companies
- `GET /api/stocks/companies` - Get list of all biotech companies
- `GET /api/stocks/prices` - Get current prices for all companies
- `GET /api/stocks/price/{ticker}` - Get price for specific ticker
- `GET /api/stocks/history/{ticker}` - Get historical data (supports periods: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
- `GET /api/stocks/upcoming-ipos` - Get upcoming IPO information

### Health
- `GET /` - Root endpoint with API information
- `GET /health` - Health check endpoint

## HKEX Ticker Format

HKEX stocks use the format: `{stock_code}.HK`
Examples:
- BeiGene: 6160.HK
- Innovent Biologics: 1801.HK
- Akeso: 9926.HK

## Data Source

Stock data is fetched from Yahoo Finance using the `yfinance` library.
