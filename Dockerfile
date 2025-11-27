# ============================================
# Dockerfile for NVIDIA GPU (CUDA)
# ============================================
# Optimized for: Systems with NVIDIA GPUs
# Base: nvidia/cuda:12.2.2-runtime-ubuntu22.04
# Requirements: Host must have NVIDIA Drivers
# and NVIDIA Container Toolkit installed.
# Run with: --gpus all
# ============================================

# ============================================
# Stage 1: Frontend Build
# ============================================
FROM node:20-alpine AS frontend-builder

WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# ============================================
# Stage 2: Backend Build (Ubuntu-based)
# ============================================
# We use the same base OS (Ubuntu 22.04) for building to ensure
# C-extensions (like pandas/numpy) are compatible with runtime.
FROM ubuntu:22.04 AS backend-builder

ENV DEBIAN_FRONTEND=noninteractive

# Install build dependencies and Python 3.12
RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common \
    gcc g++ libpq-dev git curl \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y python3.12 python3.12-venv python3.12-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python3.12 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
WORKDIR /build
COPY backend/pyproject.toml ./
COPY backend/app ./app
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# ============================================
# Stage 3: Runtime Image (NVIDIA CUDA)
# ============================================
FROM nvidia/cuda:12.2.2-runtime-ubuntu22.04

LABEL org.opencontainers.image.title="Digital Article - NVIDIA CUDA"
LABEL org.opencontainers.image.description="GPU-accelerated execution with NVIDIA CUDA"

ENV DEBIAN_FRONTEND=noninteractive

# Install runtime dependencies & Python 3.12
RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common \
    libpq-dev \
    nginx \
    supervisor \
    curl ca-certificates \
    # Install Python 3.12
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y python3.12 python3.12-venv \
    && rm -rf /var/lib/apt/lists/*

# Set python (not python3) to point to python3.12 to avoid breaking system tools
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1

# Copy Ollama binary
COPY --from=ollama/ollama:latest /bin/ollama /usr/local/bin/ollama

# Copy Python virtual environment from backend-builder
COPY --from=backend-builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy frontend build
COPY --from=frontend-builder /build/dist /usr/share/nginx/html

# Application Setup
WORKDIR /app
COPY backend/ ./backend/
COPY config.json ./config.json
COPY docker/monolithic/nginx.conf /etc/nginx/conf.d/default.conf
RUN rm -f /etc/nginx/sites-enabled/default /etc/nginx/sites-available/default 2>/dev/null || true
COPY docker/monolithic/supervisord.conf /etc/supervisor/conf.d/digitalarticle.conf
COPY docker/monolithic/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create directories
RUN mkdir -p /app/data/notebooks /app/data/workspace /app/logs /models /var/log/supervisor

# Environment
ENV NOTEBOOKS_DIR=/app/data/notebooks \
    WORKSPACE_DIR=/app/data/workspace \
    OLLAMA_MODELS=/models \
    OLLAMA_BASE_URL=http://localhost:11434 \
    PYTHONUNBUFFERED=1 \
    LOG_LEVEL=INFO \
    DIGITAL_ARTICLE_VARIANT="NVIDIA CUDA (GPU)" \
    # NVIDIA specific
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:80/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]

