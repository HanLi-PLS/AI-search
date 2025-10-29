#!/bin/bash

# AI Document Search Tool - Stop Script

echo "🛑 Stopping AI Document Search Tool..."

docker-compose down

echo "✅ Services stopped successfully!"
echo ""
echo "To start again: ./start.sh"
echo "To remove all data: docker-compose down -v"
