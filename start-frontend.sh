#!/bin/bash

echo "Starting AI Search Frontend..."
echo "Frontend will be available at http://localhost:5173"
echo ""

cd "$(dirname "$0")/frontend"

# Run the Vite dev server
npm run dev
