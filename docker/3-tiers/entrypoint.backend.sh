#!/bin/bash
set -e

# Entrypoint script for Digital Article backend (3-tier deployment)
# Prioritizes environment variables over config.json

echo "🚀 Digital Article Backend - Entrypoint"
echo "========================================"

# ========================================
# 1. ENVIRONMENT VARIABLES (from docker-compose.yml)
# ========================================
# These are set by docker-compose.yml or passed via -e
LLM_PROVIDER="${LLM_PROVIDER:-ollama}"
LLM_MODEL="${LLM_MODEL:-gemma3n:e2b}"
OLLAMA_URL="${OLLAMA_BASE_URL:-http://ollama:11434}"
DA_CONTACT_EMAIL="${DA_CONTACT_EMAIL:-lpalbou@gmail.com}"

# ========================================
# 2. VERIFY DIRECTORIES
# ========================================
echo "📁 Verifying directories..."
for dir in /app/notebooks /app/data /app/logs /models/huggingface; do
    if [ -d "$dir" ]; then
        echo "  ✅ $dir exists"
    else
        echo "  ⚠️  $dir missing (creating...)"
        mkdir -p "$dir" || echo "  ❌ Failed to create $dir (may be volume mount issue)"
    fi
done
echo "✅ Directory check complete"
echo ""

# ========================================
# 3. WAIT FOR OLLAMA (if using Ollama provider)
# ========================================
if [ "$LLM_PROVIDER" = "ollama" ]; then
    echo "🤖 Ollama provider detected - waiting for service..."
    echo "  Ollama URL: $OLLAMA_URL"

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
else
    echo "📡 Using external LLM provider: $LLM_PROVIDER"
    echo ""
fi

# ========================================
# 4. DISPLAY CONFIGURATION SUMMARY
# ========================================
echo "=================================================="
echo "Configuration Summary"
echo "=================================================="
echo "  LLM Provider:    $LLM_PROVIDER"
echo "  LLM Model:       $LLM_MODEL"
if [ "$LLM_PROVIDER" = "ollama" ]; then
    echo "  Ollama URL:      $OLLAMA_URL"
fi
if [ "$LLM_PROVIDER" = "lmstudio" ]; then
    echo "  LMStudio URL:    ${LMSTUDIO_BASE_URL:-http://host.docker.internal:1234/v1}"
fi
echo "  HF_HOME:         ${HF_HOME:-/models/huggingface}"
echo "  Notebooks:       /app/notebooks (volume)"
echo "  Data:            /app/data (volume)"
echo "  Logs:            /app/logs (volume)"
echo "  CORS:            ${CORS_ORIGINS:-*}"
echo "  Contact:         ${DA_CONTACT_EMAIL}"
echo "=================================================="
echo ""

# Show provider-specific hints
case "$LLM_PROVIDER" in
    openai)
        if [ -z "$OPENAI_API_KEY" ]; then
            echo "⚠️  OPENAI_API_KEY not set"
        else
            echo "✅ OpenAI API key configured"
        fi
        ;;
    anthropic)
        if [ -z "$ANTHROPIC_API_KEY" ]; then
            echo "⚠️  ANTHROPIC_API_KEY not set"
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

# ========================================
# 5. START BACKEND
# ========================================
echo "🚀 Starting uvicorn on port 8000..."
exec uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
