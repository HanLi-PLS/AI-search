# AI Search Platform with HKEX Biotech Stock Tracker

A comprehensive AI-powered search platform with integrated HKEX 18A biotech company stock tracking functionality.

## Features

### 🔍 AI Search (Coming Soon)
- Advanced document search and retrieval
- RAG (Retrieval-Augmented Generation) powered Q&A
- Multi-format document support

### 📊 HKEX Biotech Stock Tracker
- Real-time stock price tracking for HKEX 18A biotech companies
- Track 20+ biotech companies including BeiGene, Innovent Biologics, Akeso, and more
- Interactive stock cards with detailed information
- Search and sort functionality
- Historical data viewing
- Market cap, volume, and price change tracking

## Project Structure

```
AI-search/
├── backend/                    # FastAPI backend
│   ├── data/                   # Stock data and company lists
│   ├── models/                 # Pydantic data models
│   ├── routers/                # API route handlers
│   ├── services/               # Business logic (stock service)
│   ├── utils/                  # Utility functions
│   ├── main.py                 # FastAPI application entry point
│   └── requirements.txt        # Python dependencies
│
├── frontend/                   # React frontend (Vite)
│   ├── src/
│   │   ├── components/         # React components (StockCard, etc.)
│   │   ├── pages/              # Page components (Home, StockTracker)
│   │   ├── services/           # API client services
│   │   ├── App.jsx             # Main app component with routing
│   │   └── main.jsx            # React entry point
│   ├── package.json
│   └── vite.config.js
│
└── old_coding/                 # Legacy Jupyter notebooks
```

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **yfinance** - Yahoo Finance data fetching
- **Pandas** - Data manipulation
- **Uvicorn** - ASGI server

### Frontend
- **React** - UI library
- **Vite** - Build tool and dev server
- **React Router** - Client-side routing
- **Axios** - HTTP client
- **Recharts** - Data visualization (planned)

## Getting Started

### Prerequisites
- Python 3.8+
- Node.js 16+
- npm or yarn

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Run the backend server:
```bash
# From the backend directory
uvicorn main:app --reload

# Or from the project root
uvicorn backend.main:app --reload
```

The API will be available at `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`
- Alternative Docs: `http://localhost:8000/redoc`

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Run the development server:
```bash
npm run dev
```

The app will be available at `http://localhost:5173`

### Running Both Services

You can run both backend and frontend simultaneously in separate terminal windows:

**Terminal 1 (Backend):**
```bash
cd backend
uvicorn main:app --reload
```

**Terminal 2 (Frontend):**
```bash
cd frontend
npm run dev
```

## API Endpoints

### Stock Tracker API

- `GET /api/stocks/companies` - Get list of all biotech companies
- `GET /api/stocks/prices` - Get current prices for all companies
- `GET /api/stocks/price/{ticker}` - Get price for specific ticker (e.g., "1801.HK")
- `GET /api/stocks/history/{ticker}?period=1mo` - Get historical data
  - Supported periods: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
- `GET /api/stocks/upcoming-ipos` - Get upcoming IPO information (placeholder)

### Health Check

- `GET /` - API information
- `GET /health` - Health check endpoint

## HKEX 18A Companies Tracked

The tracker monitors 20+ biotech companies listed under HKEX Chapter 18A, including:

- **BeiGene Ltd.** (6160.HK)
- **Innovent Biologics Inc.** (1801.HK)
- **Akeso Inc.** (9926.HK)
- **Shanghai Henlius Biotech Inc.** (2696.HK)
- **Shanghai Junshi Biosciences** (1877.HK)
- **CanSino Biologics Inc.** (6185.HK)
- And many more...

## Features in Development

- [ ] Historical price charts with Recharts
- [ ] Real-time price updates via WebSocket
- [ ] IPO tracker with actual HKEX API integration
- [ ] Company financial data and analysis
- [ ] Portfolio tracking
- [ ] Price alerts and notifications
- [ ] Integration with AI search for company research

## Data Source

Stock data is fetched from Yahoo Finance using the `yfinance` library. The data is provided for informational and educational purposes only.

## Disclaimer

This application is for informational and educational purposes only. It is not financial advice. Always conduct your own research and consult with a qualified financial advisor before making investment decisions.

## License

This project is for educational purposes.

## Contributing

Feel free to open issues or submit pull requests for improvements.
