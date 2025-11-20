#!/bin/bash
# Initialize Ollama with qwen3-coder:30b model

set -e

echo "=================================================="
echo "Digital Article - Ollama Model Initialization"
echo "=================================================="
echo ""

# Wait for Ollama service to be ready
echo "⏳ Waiting for Ollama service to be ready..."
until docker exec digitalarticle-ollama ollama list &>/dev/null; do
    echo "   Ollama not ready yet, waiting 5 seconds..."
    sleep 5
done
echo "✅ Ollama service is ready!"
echo ""

# Check if model already exists
echo "🔍 Checking for existing qwen3-coder:30b model..."
if docker exec digitalarticle-ollama ollama list | grep -q "qwen3-coder:30b"; then
    echo "✅ Model qwen3-coder:30b already exists!"
    echo ""
    echo "Model details:"
    docker exec digitalarticle-ollama ollama list | grep "qwen3-coder:30b"
else
    echo "📥 Pulling qwen3-coder:30b model..."
    echo "⚠️  This is a 17GB download and may take 10-30 minutes"
    echo "   depending on your internet connection."
    echo ""

    # Pull the model with progress
    docker exec digitalarticle-ollama ollama pull qwen3-coder:30b

    echo ""
    echo "✅ Model qwen3-coder:30b downloaded successfully!"
fi

echo ""
echo "🔥 Warming up model (loading into memory)..."
echo "   This ensures fast response on first code generation."
docker exec digitalarticle-ollama ollama run qwen3-coder:30b "print('Hello')" > /dev/null 2>&1 || echo "⚠️  Warm-up skipped (optional)"

echo ""
echo "=================================================="
echo "🎉 Ollama initialization complete!"
echo "=================================================="
echo ""
echo "You can now use Digital Article with qwen3-coder:30b"
echo "Access the application at: http://localhost"
echo ""
