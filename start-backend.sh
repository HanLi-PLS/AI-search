#!/bin/bash

echo "Starting HKEX Biotech Stock Tracker Backend..."
echo "Backend will be available at http://localhost:8000"
echo "API Documentation at http://localhost:8000/docs"
echo ""

cd "$(dirname "$0")"

# Set environment variable for setuptools compatibility
export SETUPTOOLS_USE_DISTUTILS=stdlib

# Run the FastAPI server
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
