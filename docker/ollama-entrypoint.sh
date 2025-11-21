#!/bin/bash
set -e

# Start Ollama service in background
/bin/ollama serve &
OLLAMA_PID=$!

# Give it a moment to start
sleep 5

# Read model from config.json if it exists
if [ -f /config.json ]; then
    MODEL=$(grep -oP '"model":\s*"\K[^"]+' /config.json 2>/dev/null || echo "")

    if [ -n "$MODEL" ]; then
        echo "Pulling model: $MODEL"
        ollama pull "$MODEL"
    fi
fi

# Keep Ollama running
wait $OLLAMA_PID
