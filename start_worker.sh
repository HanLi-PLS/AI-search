#!/bin/bash
# Startup script for AI Search worker with virtual environment

# Activate virtual environment
source venv/bin/activate

# Start worker
python3 -m backend.app.workers.job_worker
