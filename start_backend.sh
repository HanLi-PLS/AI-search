#!/bin/bash
# Startup script for AI Search backend with virtual environment

# Activate virtual environment
source venv/bin/activate

# Start uvicorn with 6 workers
# Uvicorn manages workers internally - works correctly with PM2 fork mode
python3 -m uvicorn backend.app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 6 \
  --timeout-keep-alive 7200
