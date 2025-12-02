# ============================================
# Multi-stage Dockerfile for Digital Article
# Unified container with Ollama + Backend + Frontend
# ============================================
#
# NOTE: This file is a copy of docker/monolithic/Dockerfile
# placed at root for PaaS platforms (Railway, Render, etc.)
# that require Dockerfile at repo root.
#
# The canonical source is docker/monolithic/Dockerfile.
# Keep both files in sync when making changes.
# ============================================

# ============================================
# Stage 1: Frontend Build
# ============================================
# Using AWS ECR Public Gallery (no rate limits) instead of Docker Hub
FROM public.ecr.aws/docker/library/node:20-alpine AS frontend-builder

WORKDIR /build

# Install dependencies
COPY frontend/package*.json ./
RUN npm ci

# Build production bundle
COPY frontend/ .
RUN npm run build

# ============================================
# Stage 2: Backend Build
# ============================================
# Using AWS ECR Public Gallery (no rate limits) instead of Docker Hub
FROM public.ecr.aws/docker/library/python:3.12-slim AS backend-builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libpq-dev git \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
WORKDIR /build
COPY backend/pyproject.toml ./
COPY backend/app ./app
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# ============================================
# Stage 3: Runtime Image
# ============================================
# Using AWS ECR Public Gallery (no rate limits) instead of Docker Hub
FROM public.ecr.aws/docker/library/python:3.12-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Python runtime
    libpq-dev \
    # Nginx
    nginx \
    # Supervisor
    supervisor \
    # Utils
    curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy Ollama binary from official Ollama image
COPY --from=ollama/ollama:latest /bin/ollama /usr/local/bin/ollama

# Copy Python virtual environment from builder
COPY --from=backend-builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy frontend build from builder
COPY --from=frontend-builder /build/dist /usr/share/nginx/html

# Set up application directory
WORKDIR /app

# Copy backend application
COPY backend/ ./backend/

# Copy version module (single source of truth)
COPY digitalarticle/ ./digitalarticle/

# Copy default configuration
COPY config.json ./config.json

# Copy configuration files
COPY docker/monolithic/nginx.conf /etc/nginx/conf.d/default.conf
RUN rm -f /etc/nginx/sites-enabled/default /etc/nginx/sites-available/default 2>/dev/null || true

COPY docker/monolithic/supervisord.conf /etc/supervisor/conf.d/digitalarticle.conf

COPY docker/monolithic/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create directories (all owned by root since we run as root)
RUN mkdir -p \
    /app/data/notebooks \
    /app/data/workspace \
    /app/logs \
    /models/ollama \
    /models/huggingface \
    /var/log/supervisor

# Environment variable defaults
# LLM Configuration (can be overridden at runtime with -e)
# Note: API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY, HUGGINGFACE_TOKEN) 
# should be passed at runtime via -e, not baked into image
ENV LLM_PROVIDER=ollama \
    LLM_MODEL=gemma3n:e2b \
    NOTEBOOKS_DIR=/app/data/notebooks \
    WORKSPACE_DIR=/app/data/workspace \
    OLLAMA_MODELS=/models/ollama \
    HF_HOME=/models/huggingface \
    OLLAMA_BASE_URL=http://localhost:11434 \
    LMSTUDIO_BASE_URL=http://localhost:1234/v1 \
    PYTHONUNBUFFERED=1 \
    LOG_LEVEL=INFO \
    DIGITAL_ARTICLE_VARIANT="Standard (CPU)"

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:80/health || exit 1

# Run entrypoint script
ENTRYPOINT ["/entrypoint.sh"]
