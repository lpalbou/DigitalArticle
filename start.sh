#!/bin/bash
# Digital Article Deployment Script
# Usage:
#   ./start.sh            - Full deployment with model download
#   ./start.sh --no-model - Skip model download (test infrastructure only)

set -e

echo "🚀 Digital Article Deployment"
echo ""

# Check if --no-model flag is set
NO_MODEL=false
if [ "$1" = "--no-model" ]; then
    NO_MODEL=true
    echo "⚡ Quick mode: Skipping model download"
fi

# Build and start all services (including Ollama)
echo "📦 Building Docker images..."
docker-compose build

echo ""
echo "🎬 Starting all services..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check status
docker-compose ps

echo ""

if [ "$NO_MODEL" = false ]; then
    echo "📥 Initializing Ollama model (this may take 10-30 minutes)..."
    ./docker/init-ollama.sh
else
    echo "⚠️  Skipping model download (--no-model flag set)"
    echo ""
    echo "Ollama is running but has no model installed."
    echo "Code generation will fail until you run:"
    echo "  ./docker/init-ollama.sh"
    echo ""
fi

echo ""
echo "✅ Digital Article is ready!"
echo ""
echo "Access the application at: http://localhost"
echo ""
