#!/bin/bash
# Startup script for AI Search backend with virtual environment

# Activate virtual environment
source venv/bin/activate

# Start uvicorn with 3 workers (reduced from 6 to prevent memory issues)
# Each worker loads ~2GB embedding model, so 3 workers = ~6GB
# Leaves headroom for file processing and API calls
python3 -m uvicorn backend.app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 3 \
  --timeout-keep-alive 7200
