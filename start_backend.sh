#!/bin/bash
# Startup script for AI Search backend with virtual environment

# Activate virtual environment
source venv/bin/activate

# Start single uvicorn worker (PM2 cluster mode handles multiple instances)
# PM2 will spawn 6 instances of this script for load balancing
python3 -m uvicorn backend.app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --timeout-keep-alive 7200
