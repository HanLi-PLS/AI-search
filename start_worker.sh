#!/bin/bash
# Startup script for AI Search parallel worker with virtual environment

# Activate virtual environment
source venv/bin/activate

# Start parallel worker (processes up to 3 jobs concurrently)
python3 -m backend.app.workers.job_worker_parallel
