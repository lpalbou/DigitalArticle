#!/bin/bash
set -e

# Entrypoint script for Digital Article backend
# Reads config.json and ensures Ollama models are ready

echo "🚀 Digital Article Backend - Entrypoint"
echo "========================================"

# Verify directories are accessible (mounted volumes)
echo "📁 Verifying directories..."
for dir in /app/notebooks /app/data /app/logs; do
    if [ -d "$dir" ]; then
        echo "  ✅ $dir exists"
    else
        echo "  ⚠️  $dir missing (creating...)"
        mkdir -p "$dir" || echo "  ❌ Failed to create $dir (may be volume mount issue)"
    fi
done

echo "✅ Directory check complete"
echo ""

# Check config.json exists
if [ ! -f /app/config.json ]; then
    echo "⚠️  config.json not found, creating default..."
    cat > /app/config.json <<'CONFIGEOF'
{
  "llm": {
    "provider": "ollama",
    "model": "gemma3n:e2b"
  }
}
CONFIGEOF
    echo "✅ Default config.json created"
fi

# Parse config.json using Python (no external dependencies needed)
echo "📝 Reading configuration from /app/config.json..."

CONFIG_JSON=$(python3 -c "
import json
try:
    with open('/app/config.json') as f:
        config = json.load(f)
        llm = config.get('llm', {})
        provider = llm.get('provider', 'unknown')
        model = llm.get('model', 'unknown')
        print(f'{provider}|{model}')
except Exception as e:
    print('unknown|unknown')
    import sys
    print(f'Error reading config: {e}', file=sys.stderr)
")

PROVIDER=$(echo "$CONFIG_JSON" | cut -d'|' -f1)
MODEL=$(echo "$CONFIG_JSON" | cut -d'|' -f2)

echo "  Provider: $PROVIDER"
echo "  Model: $MODEL"
echo ""

# If provider is Ollama, wait for service to be ready
if [ "$PROVIDER" = "ollama" ]; then
    echo "🤖 Ollama provider detected - waiting for service..."

    OLLAMA_URL="${OLLAMA_BASE_URL:-http://ollama:11434}"
    echo "  Ollama URL: $OLLAMA_URL"
    echo ""

    # Wait for Ollama service to be ready (with timeout)
    echo "⏳ Waiting for Ollama service to be ready..."
    MAX_RETRIES=30
    RETRY_COUNT=0

    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if curl -sf "$OLLAMA_URL/api/tags" > /dev/null 2>&1; then
            echo "✅ Ollama service is ready!"
            break
        fi
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
            echo "⚠️  Ollama service not available after ${MAX_RETRIES} attempts (60 seconds)"
            echo "   Backend will start anyway (LLM features will fail until Ollama is ready)"
            break
        fi
        sleep 2
    done

    echo ""
fi

# Display startup configuration summary
echo "=================================================="
echo "Configuration Summary"
echo "=================================================="
echo "  LLM Provider: $PROVIDER"
echo "  LLM Model: $MODEL"
echo "  Ollama URL: ${OLLAMA_BASE_URL:-http://ollama:11434}"
echo "  Notebooks: /app/notebooks (volume)"
echo "  Data: /app/data (volume)"
echo "  Logs: /app/logs (volume)"
echo "  CORS: ${CORS_ORIGINS:-*}"
echo "=================================================="
echo ""

# Start uvicorn
echo "🚀 Starting uvicorn on port 8000..."
exec uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
