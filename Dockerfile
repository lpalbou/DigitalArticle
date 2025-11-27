# syntax=docker/dockerfile:1
# ============================================
# Multi-stage Dockerfile for Digital Article
# Unified container: Nginx + Python Backend + Ollama + Supervisor
# Deployment Target: AWS EKS (Kubernetes)
# ============================================

# ============================================
# Stage 1: Frontend Build (Node.js)
# ============================================
FROM node:20-alpine AS frontend-builder

WORKDIR /build

# 1. Install dependencies (Cached Layer)
# We copy ONLY package files first to leverage Docker layer caching.
# If package.json doesn't change, this step is skipped on rebuilds.
COPY frontend/package*.json ./
RUN npm ci

# 2. Build production bundle (Frequent Changes)
COPY frontend/ .
RUN npm run build

# ============================================
# Stage 2: Backend Build (Python)
# ============================================
FROM python:3.12-slim AS backend-builder

# Install minimal build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /build

# 1. Install Python Dependencies (Cached Layer)
# Copying toml first allows caching dependencies even if application code changes
COPY backend/pyproject.toml ./

# Upgrade pip and install dependencies defined in pyproject.toml
# Note: If your pyproject.toml requires local source to resolve dependencies,
# you might need to copy app code earlier. Assuming standard dependency definitions here.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir . || true
    # '|| true' allows the build to proceed if "." fails due to missing source code,
    # effectively pre-caching downloaded wheels.

# 2. Install Application (Frequent Changes)
COPY backend/app ./app
RUN pip install --no-cache-dir .

# ============================================
# Stage 3: Runtime Image (Production Monolith)
# ============================================
FROM python:3.12-slim

# LABELs are best practice for ECR/EKS metadata
LABEL org.opencontainers.image.title="Digital Article Unified"
LABEL org.opencontainers.image.description="Monolithic container with Nginx, Python, and Ollama"

# Install runtime dependencies
# 'procps' is added for 'ps' command, useful for debugging Supervisor
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    nginx \
    supervisor \
    curl \
    ca-certificates \
    procps \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------
# OLLAMA SETUP
# ---------------------------------------------------
# Copying the binary works for CPU inference on Debian-based images.
COPY --from=ollama/ollama:latest /bin/ollama /usr/local/bin/ollama

# ---------------------------------------------------
# FILESYSTEM SETUP
# ---------------------------------------------------
# Copy Python virtual environment
COPY --from=backend-builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy frontend build to Nginx directory
COPY --from=frontend-builder /build/dist /usr/share/nginx/html

WORKDIR /app

# Copy backend application code
COPY backend/ ./backend/

# Copy configuration files
# Using explicit naming helps avoid confusion
COPY config.json ./config.json
COPY docker/nginx-unified.conf /etc/nginx/conf.d/default.conf
COPY docker/supervisord.conf /etc/supervisor/conf.d/digitalarticle.conf
COPY docker/entrypoint-unified.sh /entrypoint.sh

# Remove default Nginx site to prevent conflicts
RUN rm -f /etc/nginx/sites-enabled/default /etc/nginx/sites-available/default 2>/dev/null || true && \
    chmod +x /entrypoint.sh

# Create data directories
RUN mkdir -p \
    /app/data/notebooks \
    /app/data/workspace \
    /app/logs \
    /models \
    /var/log/supervisor

# ---------------------------------------------------
# PERSISTENCE & ENVIRONMENT
# ---------------------------------------------------
# VOLUME declaration tells EKS/Docker that these paths hold state.
# NOTE: You MUST map a PersistentVolumeClaim (PVC) to these paths in your K8s config
# or data WILL BE LOST on pod restart.
VOLUME ["/models", "/app/data"]

ENV NOTEBOOKS_DIR=/app/data/notebooks \
    WORKSPACE_DIR=/app/data/workspace \
    OLLAMA_MODELS=/models \
    OLLAMA_BASE_URL=http://localhost:11434 \
    PYTHONUNBUFFERED=1 \
    LOG_LEVEL=INFO

# Expose HTTP port
EXPOSE 80

# Health check (Critical for EKS readiness probes)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:80/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]