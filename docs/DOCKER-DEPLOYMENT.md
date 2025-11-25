# Digital Article - Single Docker Image Deployment Guide

This guide provides step-by-step instructions for deploying Digital Article using the unified single Docker image.

---

## Prerequisites

### System Requirements

- **Docker**: Version 20.10+ (with BuildKit support)
- **RAM**: Minimum 8GB, recommended 32GB+ (for LLM inference)
- **Disk Space**: ~20GB (2.5GB image + 17GB model)
- **CPU**: Minimum 4 cores, recommended 8+ cores
- **OS**: Linux, macOS, or Windows with WSL2

### Verify Docker Installation

```bash
docker --version
# Should show: Docker version 20.10.x or higher

docker compose version
# Should show: Docker Compose version v2.x.x or higher
```

---

## Option 1: Quick Start (Recommended)

### Step 1: Clone and Navigate to Project

```bash
# Clone the repository
git clone <repository-url>
cd DigitalArticle

# Switch to the docker-onefile branch
git checkout docker-onefile
```

### Step 2: Build the Unified Image

**Important**: Run this command from the **project root directory** (where `config.json` is located).

```bash
# Build from project root
docker build -f docker/Dockerfile.unified -t digitalarticle:unified .

# Expected output:
# - Stage 1/3: Building frontend...
# - Stage 2/3: Building backend...
# - Stage 3/3: Assembling runtime...
# - Successfully tagged digitalarticle:unified

# Verify image was created
docker images | grep digitalarticle
# Should show: digitalarticle   unified   <image-id>   <size>   <time-ago>
```

**Build time**: 5-10 minutes (depending on your system)

### Step 3: Run the Container

```bash
# Run with default configuration
docker run -d \
  --name digitalarticle \
  -p 80:80 \
  -v digitalarticle-data:/app/data \
  -v digitalarticle-models:/models \
  digitalarticle:unified

# Expected output: <container-id>
```

### Step 4: Monitor Startup

```bash
# Watch the startup logs
docker logs -f digitalarticle

# You should see:
# 1. "Initializing directories..."
# 2. "Starting supervisord..."
# 3. "Waiting for Ollama to be ready..."
# 4. "Checking model availability..."
# 5. "Pulling model..." (first run only, takes 10-30 minutes)
# 6. "Starting backend service..."
# 7. "Starting nginx..."
# 8. "Digital Article - Ready!"

# Press Ctrl+C to stop following logs
```

**First startup**: 10-30 minutes (model download)
**Subsequent startups**: 90-120 seconds (model cached)

### Step 5: Access the Application

```bash
# Open in browser
open http://localhost
# Or on Linux: xdg-open http://localhost
# Or manually navigate to: http://localhost

# Test backend API
curl http://localhost/api/health
# Should return: {"status":"ok"}

# Test Ollama (from inside container)
docker exec digitalarticle curl http://localhost:11434/api/tags
# Should show: {"models":[{"name":"qwen3-coder:30b",...}]}
```

### Step 6: Verify Services Running

```bash
# Check all services are running
docker exec digitalarticle supervisorctl status

# Expected output:
# backend    RUNNING   pid 123, uptime 0:01:23
# nginx      RUNNING   pid 124, uptime 0:01:20
# ollama     RUNNING   pid 122, uptime 0:01:30
```

**✅ Deployment Complete!**

---

## Option 2: Docker Compose (Alternative)

If you prefer using Docker Compose, create a `docker-compose-unified.yml` file:

### Step 1: Create Compose File

```bash
# From project root, create docker-compose-unified.yml
cat > docker-compose-unified.yml <<'EOF'
version: '3.8'

services:
  digitalarticle:
    build:
      context: .
      dockerfile: docker/Dockerfile.unified
    image: digitalarticle:unified
    container_name: digitalarticle
    ports:
      - "80:80"
    volumes:
      - digitalarticle-data:/app/data
      - digitalarticle-models:/models
    environment:
      - NOTEBOOKS_DIR=/app/data/notebooks
      - WORKSPACE_DIR=/app/data/workspace
      - OLLAMA_MODELS=/models
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:80/health"]
      interval: 30s
      timeout: 10s
      start_period: 120s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: '10'
          memory: 36G
        reservations:
          memory: 8G

volumes:
  digitalarticle-data:
    name: digitalarticle-data
  digitalarticle-models:
    name: digitalarticle-models
EOF
```

### Step 2: Build and Run

```bash
# Build and start
docker compose -f docker-compose-unified.yml up -d --build

# View logs
docker compose -f docker-compose-unified.yml logs -f

# Stop
docker compose -f docker-compose-unified.yml down

# Stop and remove volumes (CAUTION: deletes all data)
docker compose -f docker-compose-unified.yml down -v
```

---

## Option 3: Custom Configuration

### Using Custom Paths

```bash
# Create directories on host
mkdir -p /my/custom/notebooks
mkdir -p /my/custom/workspace
mkdir -p /my/custom/models

# Run with custom paths
docker run -d \
  --name digitalarticle-custom \
  -p 80:80 \
  -v /my/custom/notebooks:/data/nb \
  -v /my/custom/workspace:/data/ws \
  -v /my/custom/models:/models \
  -e NOTEBOOKS_DIR=/data/nb \
  -e WORKSPACE_DIR=/data/ws \
  -e OLLAMA_MODELS=/models \
  digitalarticle:unified
```

### Using Different Port

```bash
# Run on port 8080 instead of 80
docker run -d \
  --name digitalarticle \
  -p 8080:80 \
  -v digitalarticle-data:/app/data \
  -v digitalarticle-models:/models \
  digitalarticle:unified

# Access at http://localhost:8080
```

### Using Different Model

Edit `config.json` before building, or mount a custom config:

```bash
# Create custom config
cat > my-config.json <<'EOF'
{
  "llm": {
    "provider": "ollama",
    "model": "llama3.2:7b"
  },
  "paths": {
    "notebooks_dir": "/app/data/notebooks",
    "workspace_dir": "/app/data/workspace"
  }
}
EOF

# Run with custom config
docker run -d \
  --name digitalarticle \
  -p 80:80 \
  -v digitalarticle-data:/app/data \
  -v digitalarticle-models:/models \
  -v $(pwd)/my-config.json:/app/config.json \
  digitalarticle:unified
```

---

## Common Operations

### View Logs

```bash
# View all logs
docker logs digitalarticle

# Follow logs (tail -f)
docker logs -f digitalarticle

# View specific service logs
docker exec digitalarticle tail -f /var/log/supervisor/backend.log
docker exec digitalarticle tail -f /var/log/supervisor/ollama.log
docker exec digitalarticle tail -f /var/log/supervisor/nginx.log

# View last 100 lines
docker exec digitalarticle tail -100 /var/log/supervisor/backend_err.log
```

### Stop and Start Container

```bash
# Stop container
docker stop digitalarticle

# Start container
docker start digitalarticle

# Restart container
docker restart digitalarticle

# Remove container (volumes persist)
docker rm -f digitalarticle
```

### Access Shell Inside Container

```bash
# Access as root
docker exec -it digitalarticle /bin/bash

# Access as appuser
docker exec -it -u appuser digitalarticle /bin/bash

# Run one-off command
docker exec digitalarticle ls -la /app/data/notebooks
```

### Check Resource Usage

```bash
# Real-time stats
docker stats digitalarticle

# Disk usage
docker exec digitalarticle du -sh /app/data /models
```

### Backup and Restore

```bash
# Backup notebooks volume
docker run --rm \
  -v digitalarticle-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/notebooks-backup-$(date +%Y%m%d).tar.gz -C /data/notebooks .

# Backup models volume
docker run --rm \
  -v digitalarticle-models:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/models-backup-$(date +%Y%m%d).tar.gz -C /data .

# Restore notebooks
docker run --rm \
  -v digitalarticle-data:/data \
  -v $(pwd):/backup \
  alpine sh -c "mkdir -p /data/notebooks && tar xzf /backup/notebooks-backup-YYYYMMDD.tar.gz -C /data/notebooks"
```

---

## Troubleshooting

### Issue: Build fails with "COPY failed"

**Cause**: Docker build not run from project root

**Solution**:
```bash
# Navigate to project root
cd /path/to/DigitalArticle

# Verify you're in the right directory
ls config.json frontend/ backend/ docker/
# Should show all these files/directories

# Build from here
docker build -f docker/Dockerfile.unified -t digitalarticle:unified .
```

### Issue: Container starts but can't access frontend

**Symptoms**: `curl http://localhost` returns connection refused

**Diagnosis**:
```bash
# Check container is running
docker ps | grep digitalarticle

# Check port mapping
docker port digitalarticle
# Should show: 80/tcp -> 0.0.0.0:80

# Check nginx is running
docker exec digitalarticle supervisorctl status nginx
```

**Solution**:
```bash
# Restart nginx
docker exec digitalarticle supervisorctl restart nginx

# Or restart entire container
docker restart digitalarticle
```

### Issue: Model downloads every time

**Symptoms**: Container takes 10-30 minutes to start every time

**Cause**: Volume not properly mounted

**Solution**:
```bash
# Check volumes
docker volume ls | grep digitalarticle

# Check volume mount
docker inspect digitalarticle | grep -A 10 Mounts

# Verify model in volume
docker exec digitalarticle ls -la /models/manifests
docker exec digitalarticle ls -la /models/blobs

# If empty, volume wasn't mounted correctly - recreate container with proper -v flag
```

### Issue: Backend fails to start

**Symptoms**: supervisorctl shows backend in FATAL state

**Diagnosis**:
```bash
# Check backend logs
docker exec digitalarticle tail -50 /var/log/supervisor/backend_err.log

# Check Python errors
docker exec digitalarticle /opt/venv/bin/python -c "import backend.app.main"
```

**Solution**:
```bash
# Restart backend
docker exec digitalarticle supervisorctl restart backend

# If still failing, check backend logs for specific error
docker exec digitalarticle cat /var/log/supervisor/backend_err.log
```

### Issue: Out of memory during LLM inference

**Symptoms**: Container crashes during notebook execution

**Solution**:
```bash
# Stop container
docker stop digitalarticle

# Run with more memory (32GB recommended for 30B models)
docker run -d \
  --name digitalarticle \
  -p 80:80 \
  -v digitalarticle-data:/app/data \
  -v digitalarticle-models:/models \
  --memory=36g \
  --memory-reservation=8g \
  digitalarticle:unified
```

---

## Production Deployment Checklist

### Before Deployment

- [ ] Verify system meets minimum requirements (8GB RAM, 20GB disk)
- [ ] Docker and Docker Compose installed and working
- [ ] Network firewall allows port 80 (or custom port)
- [ ] SSL/TLS certificate ready (if using HTTPS reverse proxy)

### Build and Test

- [ ] Build image successfully from project root
- [ ] Image size is ~2.3-2.5GB
- [ ] Test container starts without errors
- [ ] All 3 services running (ollama, backend, nginx)
- [ ] Frontend accessible at http://localhost
- [ ] API responds at http://localhost/api/health
- [ ] Create test notebook and execute cell
- [ ] Verify notebooks persist after restart

### Production Configuration

- [ ] Use named volumes (not bind mounts) for persistence
- [ ] Set memory limits appropriate for model size
- [ ] Configure restart policy: `--restart unless-stopped`
- [ ] Set up reverse proxy (nginx/traefik) for HTTPS
- [ ] Configure CORS_ORIGINS for your domain
- [ ] Set up regular backups of volumes
- [ ] Monitor disk space (models can be large)
- [ ] Set up log rotation for supervisor logs

### Security Considerations

- [ ] Run behind reverse proxy with SSL/TLS
- [ ] Restrict CORS_ORIGINS to your domain
- [ ] Use Docker secrets for sensitive config
- [ ] Keep Docker and base images updated
- [ ] Monitor container resource usage
- [ ] Set up firewall rules (only expose necessary ports)

---

## Environment Variables Reference

| Variable | Purpose | Default | Required |
|----------|---------|---------|----------|
| `NOTEBOOKS_DIR` | Notebook JSON storage path | `notebooks` | No |
| `WORKSPACE_DIR` | Per-notebook workspace root | `backend/notebook_workspace` | No |
| `OLLAMA_MODELS` | Ollama model storage path | `/models` | No |
| `OLLAMA_BASE_URL` | Ollama API endpoint | `http://localhost:11434` | No |
| `PYTHONUNBUFFERED` | Python unbuffered output | `1` | No |
| `LOG_LEVEL` | Logging verbosity | `INFO` | No |
| `CORS_ORIGINS` | CORS allowed origins | `*` | No |

---

## Next Steps

- **Customize LLM model**: Edit `config.json` before building
- **Enable GPU support**: Add `--gpus all` flag (requires nvidia-docker)
- **Set up HTTPS**: Use reverse proxy (nginx, traefik, caddy)
- **Enable authentication**: Add auth middleware (not included by default)
- **Scale horizontally**: Deploy multiple instances with load balancer
- **Monitor performance**: Use Prometheus + Grafana
- **Automated backups**: Set up cron jobs for volume backups

---

## Support and Documentation

- **Implementation Report**: `docs/devnotes/docker-one-image.md`
- **Architecture Details**: See `docs/devnotes/docker-one-image.md` - Implementation Details section
- **Migration Guide**: See `docs/devnotes/docker-one-image.md` - Migration from 3-Container Setup
- **Troubleshooting**: See `docs/devnotes/docker-one-image.md` - Troubleshooting section

---

**Last Updated**: 2025-11-25
**Branch**: `docker-onefile`
**Status**: Production Ready ✅
