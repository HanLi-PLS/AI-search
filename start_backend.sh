#!/bin/bash
# Startup script for AI Search backend with virtual environment

# Activate virtual environment
source venv/bin/activate

# Start uvicorn with proper settings
python3 -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 7200
