#!/bin/bash
set -e

echo "=================================================="
echo "Digital Article - 2-Tiers Container"
echo "(Frontend + Backend only, no bundled Ollama)"
echo "=================================================="
echo ""

# ========================================
# 1. INITIALIZE CONFIGURATION FROM ENV VARS
# ========================================
export LLM_PROVIDER="${LLM_PROVIDER:-openai-compatible}"
export LLM_MODEL="${LLM_MODEL:-}"
export NOTEBOOKS_DIR="${NOTEBOOKS_DIR:-/app/data/notebooks}"
export WORKSPACE_DIR="${WORKSPACE_DIR:-/app/data/workspace}"
export HF_HOME="${HF_HOME:-/models/huggingface}"

# API keys - default to empty if not provided
export OPENAI_API_KEY="${OPENAI_API_KEY:-}"
export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}"
export HUGGINGFACE_TOKEN="${HUGGINGFACE_TOKEN:-}"
export VLLM_API_KEY="${VLLM_API_KEY:-}"
export OPENAI_COMPATIBLE_API_KEY="${OPENAI_COMPATIBLE_API_KEY:-}"

# Provider base URLs (default to host.docker.internal for host access)
export OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://host.docker.internal:11434}"
export LMSTUDIO_BASE_URL="${LMSTUDIO_BASE_URL:-http://host.docker.internal:1234/v1}"
export VLLM_BASE_URL="${VLLM_BASE_URL:-http://host.docker.internal:8000/v1}"
export OPENAI_COMPATIBLE_BASE_URL="${OPENAI_COMPATIBLE_BASE_URL:-http://host.docker.internal:1234/v1}"

echo "📁 Initializing directories..."
mkdir -p "$NOTEBOOKS_DIR" "$WORKSPACE_DIR" /app/logs /var/log/supervisor
echo "  Notebooks: $NOTEBOOKS_DIR"
echo "  Workspace: $WORKSPACE_DIR"
echo "✅ Directories initialized"
echo ""

# ========================================
# 2. START SUPERVISORD IN BACKGROUND
# ========================================
echo "🎬 Starting supervisord..."
/usr/bin/supervisord -c /etc/supervisor/supervisord.conf &
SUPERVISOR_PID=$!
sleep 2

# ========================================
# 3. TEST EXTERNAL PROVIDER CONNECTIVITY
# ========================================
echo "🔌 Testing LLM provider connectivity..."

case "$LLM_PROVIDER" in
    ollama)
        if curl -sf "$OLLAMA_BASE_URL/api/tags" > /dev/null 2>&1; then
            echo "✅ Ollama reachable at $OLLAMA_BASE_URL"
        else
            echo "⚠️  Cannot reach Ollama at $OLLAMA_BASE_URL"
            echo "   Make sure Ollama is running on host"
        fi
        ;;
    lmstudio)
        if curl -sf "$LMSTUDIO_BASE_URL/models" > /dev/null 2>&1; then
            echo "✅ LMStudio reachable at $LMSTUDIO_BASE_URL"
        else
            echo "⚠️  Cannot reach LMStudio at $LMSTUDIO_BASE_URL"
            echo "   Make sure LMStudio is running on host"
        fi
        ;;
    vllm)
        if curl -sf "$VLLM_BASE_URL/models" > /dev/null 2>&1; then
            echo "✅ vLLM reachable at $VLLM_BASE_URL"
        else
            echo "⚠️  Cannot reach vLLM at $VLLM_BASE_URL"
        fi
        ;;
    openai-compatible)
        if curl -sf "$OPENAI_COMPATIBLE_BASE_URL/models" > /dev/null 2>&1; then
            echo "✅ OpenAI-compatible server reachable at $OPENAI_COMPATIBLE_BASE_URL"
        else
            echo "⚠️  Cannot reach OpenAI-compatible at $OPENAI_COMPATIBLE_BASE_URL"
        fi
        ;;
    openai)
        echo "📡 Using OpenAI cloud API"
        [ -z "$OPENAI_API_KEY" ] && echo "⚠️  OPENAI_API_KEY not set"
        ;;
    anthropic)
        echo "📡 Using Anthropic cloud API"
        [ -z "$ANTHROPIC_API_KEY" ] && echo "⚠️  ANTHROPIC_API_KEY not set"
        ;;
    *)
        echo "📡 Using provider: $LLM_PROVIDER"
        ;;
esac
echo ""

# ========================================
# 4. START BACKEND
# ========================================
echo "🚀 Starting backend service..."
/usr/bin/supervisorctl start backend

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
        break
    fi
    sleep 2
done
echo ""

# ========================================
# 5. START NGINX
# ========================================
echo "🌐 Starting nginx..."
/usr/bin/supervisorctl start nginx
sleep 2
echo "✅ Nginx started"
echo ""

# ========================================
# 6. DISPLAY CONFIGURATION SUMMARY
# ========================================
echo "=================================================="
echo "Digital Article - Ready!"
echo "=================================================="
echo ""
echo "Services:"
echo "  Frontend:    http://localhost:80"
echo "  Backend API: http://localhost:8000"
echo ""
echo "Configuration:"
echo "  Image Type:   ${DIGITAL_ARTICLE_VARIANT:-2-Tiers}"
echo "  LLM Provider: $LLM_PROVIDER"
echo "  LLM Model:    $LLM_MODEL"
echo "  Notebooks:    $NOTEBOOKS_DIR"
echo "  Workspace:    $WORKSPACE_DIR"
echo ""
echo "External Provider URLs:"
echo "  Ollama:            $OLLAMA_BASE_URL"
echo "  LMStudio:          $LMSTUDIO_BASE_URL"
echo "  vLLM:              $VLLM_BASE_URL"
echo "  OpenAI-Compatible: $OPENAI_COMPATIBLE_BASE_URL"
echo ""
echo "Logs:"
echo "  docker exec <container> tail -f /var/log/supervisor/backend.log"
echo "=================================================="
echo ""

# ========================================
# 7. HAND OFF TO SUPERVISORD (FOREGROUND)
# ========================================
echo "🎬 Running (Ctrl+C to stop)..."
wait $SUPERVISOR_PID
