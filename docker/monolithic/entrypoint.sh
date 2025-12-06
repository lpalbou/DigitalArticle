#!/bin/bash
set -e

echo "=================================================="
echo "Digital Article - Unified Container"
echo "=================================================="
echo ""

# ========================================
# 1. INITIALIZE CONFIGURATION FROM ENV VARS
# ========================================
# Environment variables (with defaults)
# Export all so supervisord can access them
export LLM_PROVIDER="${LLM_PROVIDER:-ollama}"
export LLM_MODEL="${LLM_MODEL:-gemma3n:e2b}"
export NOTEBOOKS_DIR="${NOTEBOOKS_DIR:-/app/data/notebooks}"
export WORKSPACE_DIR="${WORKSPACE_DIR:-/app/data/workspace}"
export OLLAMA_MODELS="${OLLAMA_MODELS:-/models/ollama}"
export HF_HOME="${HF_HOME:-/models/huggingface}"

# API keys - default to empty if not provided (for supervisord compatibility)
export OPENAI_API_KEY="${OPENAI_API_KEY:-}"
export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}"
export HUGGINGFACE_TOKEN="${HUGGINGFACE_TOKEN:-}"

# Provider base URLs (for external servers)
export OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"
export LMSTUDIO_BASE_URL="${LMSTUDIO_BASE_URL:-http://localhost:1234/v1}"

echo "📁 Initializing directories..."
echo "  Notebooks: $NOTEBOOKS_DIR"
echo "  Workspace: $WORKSPACE_DIR"

# Create directories (running as root, no permission issues)
mkdir -p "$NOTEBOOKS_DIR" "$WORKSPACE_DIR" /app/logs /var/log/supervisor

# ========================================
# 2. PROVIDER-AWARE STARTUP
# ========================================
USE_LOCAL_OLLAMA=false

if [ "$LLM_PROVIDER" = "ollama" ]; then
    # Check if OLLAMA_BASE_URL points to localhost or external server
    if echo "$OLLAMA_BASE_URL" | grep -qE "(localhost|127\.0\.0\.1)"; then
        USE_LOCAL_OLLAMA=true
        mkdir -p "$OLLAMA_MODELS"
        echo "📦 Using LOCAL Ollama server"
        echo "  Models: $OLLAMA_MODELS"
    else
        echo "📡 Using EXTERNAL Ollama server: $OLLAMA_BASE_URL"
        echo "  (Local Ollama will NOT be started)"
    fi
fi

echo "✅ Directories initialized"
echo ""

# ========================================
# 3. START SUPERVISORD IN BACKGROUND
# ========================================
echo "🎬 Starting supervisord..."
/usr/bin/supervisord -c /etc/supervisor/supervisord.conf &
SUPERVISOR_PID=$!

# Give supervisor time to start services
sleep 3

# ========================================
# 4. OLLAMA SETUP (Only if using LOCAL Ollama)
# ========================================
if [ "$USE_LOCAL_OLLAMA" = true ]; then
    echo "⏳ Waiting for local Ollama to be ready..."
    MAX_RETRIES=30
    RETRY_COUNT=0

    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
            echo "✅ Local Ollama is ready!"
            break
        fi
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
            echo "⚠️  Local Ollama not ready after 60 seconds"
            break
        fi
        sleep 2
    done
    echo ""

    # Auto-pull model if using local Ollama
    echo "📦 Checking model availability..."
    echo "  Configured model: $LLM_MODEL"

    if curl -sf http://localhost:11434/api/tags | grep -q "\"name\":\"$LLM_MODEL\""; then
        echo "  ✅ Model already available (cached in volume)"
    else
        echo "  ⏬ Pulling model (this may take a while)..."
        /usr/local/bin/ollama pull "$LLM_MODEL" || echo "  ⚠️  Model pull failed"
    fi
    echo ""

elif [ "$LLM_PROVIDER" = "ollama" ]; then
    # External Ollama - verify connectivity
    echo "🔌 Testing connection to external Ollama..."
    if curl -sf "$OLLAMA_BASE_URL/api/tags" > /dev/null 2>&1; then
        echo "✅ External Ollama is reachable at $OLLAMA_BASE_URL"

        # Check if model exists on external server
        if curl -sf "$OLLAMA_BASE_URL/api/tags" | grep -q "\"name\":\"$LLM_MODEL\""; then
            echo "✅ Model $LLM_MODEL is available on external server"
        else
            echo "⚠️  Model $LLM_MODEL not found on external server"
            echo "   Available models:"
            curl -sf "$OLLAMA_BASE_URL/api/tags" | grep -oP '"name":"\K[^"]+' | head -5 | while read m; do
                echo "   - $m"
            done
        fi
    else
        echo "⚠️  Cannot reach external Ollama at $OLLAMA_BASE_URL"
        echo "   Backend will retry on startup"
    fi

    # Stop local Ollama (not needed)
    /usr/bin/supervisorctl stop ollama 2>/dev/null || true
    echo ""
else
    # Non-Ollama provider
    echo "📡 Using external LLM provider: $LLM_PROVIDER"
    /usr/bin/supervisorctl stop ollama 2>/dev/null || true
    echo ""
fi

# ========================================
# 5. START BACKEND
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
# 6. START NGINX
# ========================================
echo "🌐 Starting nginx..."
/usr/bin/supervisorctl start nginx
sleep 2
echo "✅ Nginx started"
echo ""

# ========================================
# 7. DISPLAY CONFIGURATION SUMMARY
# ========================================
echo "=================================================="
echo "Digital Article - Ready!"
echo "=================================================="
echo ""
echo "Services:"
echo "  Frontend:    http://localhost:80"
echo "  Backend API: http://localhost:8000"
if [ "$USE_LOCAL_OLLAMA" = true ]; then
    echo "  Ollama API:  http://localhost:11434 (local)"
elif [ "$LLM_PROVIDER" = "ollama" ]; then
    echo "  Ollama API:  $OLLAMA_BASE_URL (external)"
fi
echo ""
echo "Configuration:"
echo "  Image Type:   ${DIGITAL_ARTICLE_VARIANT:-Standard}"
echo "  LLM Provider: $LLM_PROVIDER"
echo "  LLM Model:    $LLM_MODEL"
echo "  Notebooks:    $NOTEBOOKS_DIR"
echo "  Workspace:    $WORKSPACE_DIR"
if [ "$USE_LOCAL_OLLAMA" = true ]; then
    echo "  Models:       $OLLAMA_MODELS"
fi
echo ""

# Show provider-specific hints
case "$LLM_PROVIDER" in
    openai)
        if [ -z "$OPENAI_API_KEY" ]; then
            echo "⚠️  OPENAI_API_KEY not set. Set it with: -e OPENAI_API_KEY=sk-..."
        else
            echo "✅ OpenAI API key configured"
        fi
        ;;
    anthropic)
        if [ -z "$ANTHROPIC_API_KEY" ]; then
            echo "⚠️  ANTHROPIC_API_KEY not set. Set it with: -e ANTHROPIC_API_KEY=..."
        else
            echo "✅ Anthropic API key configured"
        fi
        ;;
    huggingface)
        if [ -z "$HUGGINGFACE_TOKEN" ]; then
            echo "ℹ️  HUGGINGFACE_TOKEN not set (optional for public models)"
        else
            echo "✅ HuggingFace token configured"
        fi
        ;;
esac

echo ""
echo "Logs:"
echo "  View with: docker exec <container> tail -f /var/log/supervisor/<service>.log"
echo "=================================================="
echo ""

# ========================================
# 8. HAND OFF TO SUPERVISORD (FOREGROUND)
# ========================================
echo "🎬 Handing off to supervisord (container will run until stopped)..."
wait $SUPERVISOR_PID
