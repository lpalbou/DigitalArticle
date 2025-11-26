#!/bin/bash
set -e

echo "=================================================="
echo "Digital Article - Unified Container"
echo "=================================================="
echo ""

# ========================================
# 1. INITIALIZE DIRECTORIES FROM ENV VARS
# ========================================
echo "📁 Initializing directories..."

NOTEBOOKS_DIR="${NOTEBOOKS_DIR:-/app/data/notebooks}"
WORKSPACE_DIR="${WORKSPACE_DIR:-/app/data/workspace}"
OLLAMA_MODELS="${OLLAMA_MODELS:-/models}"

echo "  Notebooks: $NOTEBOOKS_DIR"
echo "  Workspace: $WORKSPACE_DIR"
echo "  Models: $OLLAMA_MODELS"
echo ""

# Create directories (running as root, no permission issues)
mkdir -p "$NOTEBOOKS_DIR" "$WORKSPACE_DIR" /app/logs "$OLLAMA_MODELS" /var/log/supervisor

echo "✅ Directories initialized"
echo ""

# ========================================
# 2. CREATE DEFAULT CONFIG.JSON IF MISSING
# ========================================
if [ ! -f /app/config.json ]; then
    echo "📝 Creating default config.json..."
    cat > /app/config.json <<'CONFIGEOF'
{
  "llm": {
    "provider": "ollama",
    "model": "qwen3-coder:30b"
  },
  "paths": {
    "notebooks_dir": "/app/data/notebooks",
    "workspace_dir": "/app/data/workspace"
  }
}
CONFIGEOF
    echo "✅ Default config.json created"
fi

# ========================================
# 3. START SUPERVISORD IN BACKGROUND
# ========================================
echo "🎬 Starting supervisord..."
/usr/bin/supervisord -c /etc/supervisor/supervisord.conf &
SUPERVISOR_PID=$!

# Give supervisor time to start Ollama
sleep 5

# ========================================
# 4. WAIT FOR OLLAMA READINESS
# ========================================
echo "⏳ Waiting for Ollama to be ready..."
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "✅ Ollama is ready!"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        echo "⚠️  Ollama not ready after 60 seconds"
        echo "   Container will start anyway (check logs with: docker logs <container>)"
        break
    fi
    sleep 2
done
echo ""

# ========================================
# 5. AUTO-PULL MODEL FROM CONFIG.JSON
# ========================================
echo "📦 Checking model availability..."

# Read model from config.json
MODEL=$(python3 -c "
import json
try:
    with open('/app/config.json') as f:
        config = json.load(f)
        print(config.get('llm', {}).get('model', ''))
except:
    print('')
")

if [ -n "$MODEL" ]; then
    echo "  Configured model: $MODEL"

    # Check if model already exists in volume
    if curl -sf http://localhost:11434/api/tags | grep -q "\"name\":\"$MODEL\""; then
        echo "  ✅ Model already available (cached in volume)"
    else
        echo "  ⏬ Pulling model (this may take a while)..."
        /usr/local/bin/ollama pull "$MODEL" || echo "  ⚠️  Model pull failed (will retry on backend startup)"
    fi
else
    echo "  ⚠️  No model configured in config.json"
fi
echo ""

# ========================================
# 6. START BACKEND
# ========================================
echo "🚀 Starting backend service..."
/usr/bin/supervisorctl start backend

# Wait for backend health
echo "⏳ Waiting for backend to be healthy..."
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ Backend is healthy!"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        echo "⚠️  Backend not healthy after 60 seconds"
        echo "   Container will start anyway (check logs)"
        break
    fi
    sleep 2
done
echo ""

# ========================================
# 7. START NGINX
# ========================================
echo "🌐 Starting nginx..."
/usr/bin/supervisorctl start nginx
sleep 2
echo "✅ Nginx started"
echo ""

# ========================================
# 8. DISPLAY CONFIGURATION SUMMARY
# ========================================
echo "=================================================="
echo "Digital Article - Ready!"
echo "=================================================="
echo "Services:"
echo "  Frontend: http://localhost:80"
echo "  Backend API: http://localhost:8000"
echo "  Ollama API: http://localhost:11434"
echo ""
echo "Configuration:"
echo "  LLM Provider: $(python3 -c "import json; print(json.load(open('/app/config.json')).get('llm',{}).get('provider','unknown'))")"
echo "  LLM Model: $MODEL"
echo "  Notebooks: $NOTEBOOKS_DIR"
echo "  Workspace: $WORKSPACE_DIR"
echo "  Models: $OLLAMA_MODELS"
echo ""
echo "Logs:"
echo "  View with: docker exec <container> tail -f /var/log/supervisor/<service>.log"
echo "=================================================="
echo ""

# ========================================
# 9. HAND OFF TO SUPERVISORD (FOREGROUND)
# ========================================
echo "🎬 Handing off to supervisord (container will run until stopped)..."
wait $SUPERVISOR_PID
