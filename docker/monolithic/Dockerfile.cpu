# ============================================
# Dockerfile for CPU-Only
# ============================================
# Optimized for: Standard x86_64 CPUs (Intel/AMD)
# Usage: Best for servers without GPUs or local
# machines without dedicated graphics.
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
# Stage 2: Backend Build
# ============================================
FROM python:3.12-slim AS backend-builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libpq-dev git \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /build
COPY backend/pyproject.toml ./
COPY backend/app ./app
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# ============================================
# Stage 3: Runtime Image
# ============================================
FROM python:3.12-slim

LABEL org.opencontainers.image.title="Digital Article - CPU"
LABEL org.opencontainers.image.description="Standard CPU-only execution"

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    nginx \
    supervisor \
    curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ollama/ollama:latest /bin/ollama /usr/local/bin/ollama

COPY --from=backend-builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY --from=frontend-builder /build/dist /usr/share/nginx/html

WORKDIR /app
COPY backend/ ./backend/
COPY config.json ./config.json
COPY docker/monolithic/nginx.conf /etc/nginx/conf.d/default.conf
RUN rm -f /etc/nginx/sites-enabled/default /etc/nginx/sites-available/default 2>/dev/null || true
COPY docker/monolithic/supervisord.conf /etc/supervisor/conf.d/digitalarticle.conf
COPY docker/monolithic/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN mkdir -p /app/data/notebooks /app/data/workspace /app/logs /models /var/log/supervisor

ENV NOTEBOOKS_DIR=/app/data/notebooks \
    WORKSPACE_DIR=/app/data/workspace \
    OLLAMA_MODELS=/models \
    OLLAMA_BASE_URL=http://localhost:11434 \
    PYTHONUNBUFFERED=1 \
    LOG_LEVEL=INFO \
    DIGITAL_ARTICLE_VARIANT="Standard (CPU)"

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:80/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]

