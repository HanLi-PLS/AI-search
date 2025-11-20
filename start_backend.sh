#!/bin/bash
# Startup script for AI Search backend with virtual environment

# Activate virtual environment
source venv/bin/activate

# Start uvicorn with multiple workers for better concurrency
# Workers = (2 * CPU cores) + 1 is a good starting point
# Each worker can handle 100+ concurrent async requests
# With 4 workers, the system can handle 50-100+ concurrent users
python3 -m uvicorn backend.app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --timeout-keep-alive 7200
