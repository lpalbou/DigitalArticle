#!/bin/bash
set -e

# Entrypoint script for Digital Article backend
# Verifies environment and starts backend

echo "🚀 Digital Article Backend - Entrypoint"
echo "========================================"

# Verify directories are accessible (mounted volumes)
echo "📁 Verifying directories..."
for dir in /app/notebooks /app/data /app/sample_data /app/logs; do
    if [ -d "$dir" ]; then
        echo "  ✅ $dir exists"
    else
        echo "  ⚠️  $dir missing (creating...)"
        mkdir -p "$dir" || echo "  ❌ Failed to create $dir (may be volume mount issue)"
    fi
done

echo "✅ Directory check complete"

# Check config.json exists
if [ ! -f /app/config.json ]; then
    echo "⚠️  config.json not found, creating default..."
    cat > /app/config.json <<EOF
{
  "llm": {
    "provider": "ollama",
    "model": "qwen3-coder:30b"
  }
}
EOF
    echo "✅ Default config.json created"
fi

# Display startup configuration
echo ""
echo "Configuration:"
echo "  - Notebooks: /app/notebooks"
echo "  - Data: /app/data"
echo "  - Config: /app/config.json"
echo "  - Ollama: ${OLLAMA_BASE_URL:-http://ollama:11434}"
echo "  - CORS: ${CORS_ORIGINS:-*}"
echo ""

# Start uvicorn
echo "🚀 Starting uvicorn..."
exec uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
