# AI Search Platform with HKEX Biotech Stock Tracker

A comprehensive AI-powered search platform with integrated HKEX 18A biotech company stock tracking functionality.

## Features

### 🔍 AI Document Search & RAG
- **Advanced Document Search** - Query your biotech documents using natural language
- **RAG (Retrieval-Augmented Generation)** - Combines vector search (ChromaDB), BM25 keyword search, and GPT-4 for intelligent answers
- **Multi-format Support** - Process PDFs, DOCX, PPTX, XLSX, CSV, HTML, Markdown
- **Image Extraction** - Extract and analyze images/tables from PDFs using GPT-4 Vision
- **Ensemble Retrieval** - Hybrid BM25 + vector semantic search for best results
- **Web Search Integration** - Optionally supplement with real-time online search
- **Company Intelligence** - Extract drug pipelines, competitors, clinical trials, and market analysis
- **Configurable Models** - Choose between GPT-4.1, O4-Mini, O3 for different speed/quality trade-offs
- **S3 Integration** - Load and process documents directly from AWS S3

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
│   │   ├── stocks.py           # Stock tracker endpoints
│   │   └── ai_search.py        # AI search endpoints
│   ├── services/               # Business logic
│   │   ├── stock_service.py    # Stock data fetching
│   │   ├── document_service.py # Document processing & PDF extraction
│   │   └── search_service.py   # ChromaDB, BM25, RAG
│   ├── utils/                  # Utility functions
│   ├── main.py                 # FastAPI application entry point
│   └── requirements.txt        # Python dependencies
│
├── frontend/                   # React frontend (Vite)
│   ├── src/
│   │   ├── components/         # React components (StockCard, etc.)
│   │   ├── pages/              # Page components (Home, StockTracker, AISearch)
│   │   ├── services/           # API client services
│   │   ├── App.jsx             # Main app component with routing
│   │   └── main.jsx            # React entry point
│   ├── package.json
│   └── vite.config.js
│
└── old_coding/                 # Legacy Jupyter notebooks (for reference)
```

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **Uvicorn** - ASGI server
- **ChromaDB** - Vector database for semantic search
- **LangChain** - RAG framework and document loaders
- **OpenAI GPT-4** - AI models for vision and text generation
- **SentenceTransformers** - Embeddings (Qwen3-Embedding-4B)
- **PyMuPDF** - PDF processing and image extraction
- **PyTorch** - ML framework with GPU support
- **BM25** - Keyword-based retrieval
- **boto3** - AWS S3 integration
- **yfinance** - Yahoo Finance stock data
- **Pandas** - Data manipulation

### Frontend
- **React 19** - UI library
- **Vite** - Build tool and dev server
- **React Router** - Client-side routing
- **Axios** - HTTP client for API calls
- **Recharts** - Data visualization (planned)

## Getting Started

### Prerequisites
- Python 3.8+
- Node.js 16+
- npm or yarn
- CUDA-capable GPU (recommended for AI search)
- OpenAI API key (required for AI search)
- AWS credentials (if using S3 for document storage)

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

### AI Search API

- `POST /api/ai-search/search` - Search documents and get AI-generated answer
  - Body: `{ "question": str, "k_bm": int, "k_jd": int, "search_model": str, "priority_order": [str] }`
  - Returns: `{ "answer": str, "online_search_response": str | null }`

- `GET /api/ai-search/status` - Get index status
  - Returns: `{ "status": str, "vector_db_loaded": bool, "bm25_loaded": bool, "embeddings_model": str, "device": str }`

- `POST /api/ai-search/index` - Index documents from S3
  - Body: `{ "s3_bucket": str, "s3_folder": str, "ignored_files": [str], "collection_name": str, "persist_directory": str }`
  - Returns: `{ "status": str, "message": str, "document_count": int }`

- `POST /api/ai-search/company-info` - Extract company intelligence
  - Params: `company_name`, `k_bm`, `k_jd`
  - Returns: Structured JSON with drug pipeline, competitors, clinical trials

### Stock Tracker API

- `GET /api/stocks/companies` - Get list of all biotech companies
- `GET /api/stocks/prices` - Get current prices for all companies
- `GET /api/stocks/price/{ticker}` - Get price for specific ticker (e.g., "1801.HK")
- `GET /api/stocks/history/{ticker}?period=1mo` - Get historical data
  - Supported periods: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
- `GET /api/stocks/upcoming-ipos` - Get upcoming IPO information (placeholder)

### Health Check

- `GET /` - API information and features list
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
