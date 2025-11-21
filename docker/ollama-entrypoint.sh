#!/bin/bash
set -e

echo "🤖 Ollama Container - Entrypoint"
echo "=================================="

# Start Ollama service in background
echo "🚀 Starting Ollama service..."
/bin/ollama serve &
OLLAMA_PID=$!

# Wait for Ollama to be ready
echo "⏳ Waiting for Ollama to be ready..."
for i in {1..30}; do
    if curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "✅ Ollama service is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Ollama failed to start"
        exit 1
    fi
    sleep 2
done

# Read model from config.json (mounted from host)
if [ -f /config.json ]; then
    echo ""
    echo "📝 Reading configuration from /config.json..."

    MODEL=$(python3 -c "
import json
try:
    with open('/config.json') as f:
        config = json.load(f)
        model = config.get('llm', {}).get('model', 'unknown')
        print(model)
except Exception as e:
    print('unknown')
    import sys
    print(f'Error reading config: {e}', file=sys.stderr)
" 2>&1)

    echo "  Model: $MODEL"
    echo ""

    if [ "$MODEL" != "unknown" ]; then
        # Check if model already exists
        echo "🔍 Checking if model '$MODEL' is available..."

        MODEL_EXISTS=$(curl -sf http://localhost:11434/api/tags 2>/dev/null | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    models = data.get('models', [])
    target = '$MODEL'
    exists = any(
        m.get('name', '').replace(':latest', '') == target.replace(':latest', '')
        for m in models
    )
    print('yes' if exists else 'no')
except:
    print('no')
" || echo "no")

        if [ "$MODEL_EXISTS" = "yes" ]; then
            echo "✅ Model '$MODEL' is already available!"
        else
            echo "📥 Model '$MODEL' not found - downloading now..."
            echo ""
            echo "ℹ️  Model sizes (approximate download times):"
            echo "   - qwen3-coder:4b   → 2.6GB   (~2-5 min)"
            echo "   - qwen3-coder:8b   → 5GB     (~5-10 min)"
            echo "   - qwen3-coder:14b  → 8.5GB   (~10-15 min)"
            echo "   - qwen3-coder:30b  → 17GB    (~15-30 min)"
            echo ""
            echo "⏳ Downloading model (this may take a while)..."
            echo ""

            # Pull model with progress
            ollama pull "$MODEL"

            echo ""
            echo "✅ Model '$MODEL' downloaded successfully!"
        fi
    fi
else
    echo "⚠️  /config.json not found - skipping model download"
    echo "   Models can be pulled manually: ollama pull <model>"
fi

echo ""
echo "=================================================="
echo "Ollama Ready"
echo "=================================================="
echo "  Available at: http://localhost:11434"
echo "  Models loaded: $(ollama list | wc -l) model(s)"
echo "=================================================="
echo ""

# Keep Ollama service running in foreground
wait $OLLAMA_PID
