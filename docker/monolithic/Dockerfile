# ============================================
# Multi-stage Dockerfile for Digital Article
# Unified container with Ollama + Backend + Frontend
# ============================================
#
# This is the CANONICAL monolithic Dockerfile.
# A copy exists at repo root (./Dockerfile) for PaaS platforms.
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

# Install build dependencies (cmake/swig/zlib needed for tellurium/SBML)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libpq-dev git cmake make swig zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
WORKDIR /build
COPY backend/pyproject.toml ./
COPY backend/app ./app
# Needed for backend dynamic version (single source of truth: `digitalarticle/_version.py`)
COPY digitalarticle/_version.py ./digitalarticle/_version.py
# CFLAGS to allow building older C extensions with newer GCC
RUN pip install --no-cache-dir --upgrade pip && \
    CFLAGS="-Wno-error=incompatible-pointer-types" pip install --no-cache-dir .

# ============================================
# Stage 3: Runtime Image
# ============================================
# Using AWS ECR Public Gallery (no rate limits) instead of Docker Hub
FROM public.ecr.aws/docker/library/python:3.12-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Python runtime
    libpq-dev \
    libgomp1 \
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

# Copy default system personas (users can extend with custom personas via volume)
COPY data/personas/system/ ./data/personas/system/

# Copy user-facing documentation for the in-app Help modal
COPY user_docs/ ./user_docs/

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
    /app/data/personas/custom \
    /app/logs \
    /models/ollama \
    /models/huggingface \
    /var/log/supervisor

# ============================================
# BUILD ARGUMENTS
# Customize at build time with --build-arg
# Example: docker build --build-arg OPENAI_COMPATIBLE_BASE_URL=http://myserver:8080/v1 ...
# ============================================
ARG LLM_PROVIDER=openai-compatible
ARG LLM_MODEL=

# Default to host.docker.internal (access host machine from container)
# For Linux without Docker Desktop: use --add-host=host.docker.internal:host-gateway
ARG OLLAMA_BASE_URL=http://host.docker.internal:11434
ARG LMSTUDIO_BASE_URL=http://host.docker.internal:1234/v1
ARG VLLM_BASE_URL=http://host.docker.internal:8000/v1
ARG OPENAI_COMPATIBLE_BASE_URL=http://host.docker.internal:1234/v1

# Environment variable defaults
# LLM Configuration (can be overridden at runtime with -e)
# Note: API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY, HUGGINGFACE_TOKEN, VLLM_API_KEY, OPENAI_COMPATIBLE_API_KEY)
# should be passed at runtime via -e, not baked into image
ENV LLM_PROVIDER=${LLM_PROVIDER} \
    LLM_MODEL=${LLM_MODEL} \
    NOTEBOOKS_DIR=/app/data/notebooks \
    WORKSPACE_DIR=/app/data/workspace \
    OLLAMA_MODELS=/models/ollama \
    HF_HOME=/models/huggingface \
    OLLAMA_BASE_URL=${OLLAMA_BASE_URL} \
    LMSTUDIO_BASE_URL=${LMSTUDIO_BASE_URL} \
    VLLM_BASE_URL=${VLLM_BASE_URL} \
    OPENAI_COMPATIBLE_BASE_URL=${OPENAI_COMPATIBLE_BASE_URL} \
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
