# Digital Article - Unified Docker Image Deployment

This guide covers deploying Digital Article as a **single Docker image** containing all three services (Ollama + Backend + Frontend).

---

## Quick Start

### Prerequisites

- Docker 20.10+ installed
- 8GB RAM minimum (32GB recommended for LLM inference)
- 20GB free disk space
- Linux, macOS, or Windows with WSL2

### Build and Run (3 Steps)

```bash
# Step 1: Navigate to project root (IMPORTANT!)
cd /path/to/DigitalArticle

# Step 2: Build the unified image (5-10 minutes)
docker build -f docker/Dockerfile.unified -t digitalarticle:unified .

# Step 3: Run the container
docker run -d \
  --name digitalarticle \
  -p 80:80 \
  -v digitalarticle-data:/app/data \
  -v digitalarticle-models:/models \
  digitalarticle:unified

# Access at http://localhost
```

**First startup**: 10-30 minutes (downloads LLM model)
**Subsequent startups**: 90-120 seconds (model cached)

---

## Architecture

### What's Inside the Container

```
┌─────────────────────────────────────────┐
│  Unified Container (Port 80)            │
│                                          │
│  ┌──────────┐  ┌──────────┐  ┌────────┐│
│  │  Ollama  │→ │ Backend  │→ │ Nginx  ││
│  │  :11434  │  │  :8000   │  │  :80   ││
│  └──────────┘  └──────────┘  └────────┘│
│                                          │
│  Managed by: supervisord                │
└─────────────────────────────────────────┘
           ↓              ↓
    [models volume]  [data volume]
     /models/        /app/data/
```

### Service Startup Sequence

1. **Supervisord** starts → launches Ollama
2. **Entrypoint** waits for Ollama readiness
3. **Entrypoint** checks/downloads LLM model (cached after first run)
4. **Entrypoint** starts Backend (FastAPI)
5. **Entrypoint** starts Nginx (serves frontend + proxies API)
6. **Ready** - All services running

---

## File Structure

```
docker/
├── Dockerfile.unified        # Multi-stage build for unified image
├── supervisord.conf          # Process management (ollama, backend, nginx)
├── nginx-unified.conf        # Nginx config (localhost:8000 backend proxy)
├── entrypoint-unified.sh     # Startup orchestration script
├── readme-unified-image.md   # This file
└── readme-multi-container.md # 3-container setup documentation
```

---

## Volume Configuration

### Two Named Volumes

**digitalarticle-data** (`/app/data/`)
- Notebooks JSON files
- Per-notebook workspace directories
- User uploaded files

**digitalarticle-models** (`/models/`)
- Ollama LLM model files (~17GB for qwen3-coder:30b)
- Cached after first download
- Persists across container restarts

### Custom Volume Paths

```bash
# Use custom host directories instead of named volumes
docker run -d \
  --name digitalarticle \
  -p 80:80 \
  -v /host/path/data:/app/data \
  -v /host/path/models:/models \
  -e NOTEBOOKS_DIR=/app/data/notebooks \
  -e WORKSPACE_DIR=/app/data/workspace \
  -e OLLAMA_MODELS=/models \
  digitalarticle:unified
```

---

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `NOTEBOOKS_DIR` | `/app/data/notebooks` | Notebook storage path |
| `WORKSPACE_DIR` | `/app/data/workspace` | Workspace root path |
| `OLLAMA_MODELS` | `/models` | LLM model storage |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API URL |
| `LOG_LEVEL` | `INFO` | Backend logging level |
| `CORS_ORIGINS` | `*` | CORS allowed origins |

---

## Common Operations

### Monitor Startup

```bash
# Follow logs
docker logs -f digitalarticle

# Check service status
docker exec digitalarticle supervisorctl status

# Should show:
# backend    RUNNING   pid 123, uptime 0:01:23
# nginx      RUNNING   pid 124, uptime 0:01:20
# ollama     RUNNING   pid 122, uptime 0:01:30
```

### View Service Logs

```bash
# Backend logs
docker exec digitalarticle tail -f /var/log/supervisor/backend.log

# Ollama logs
docker exec digitalarticle tail -f /var/log/supervisor/ollama.log

# Nginx logs
docker exec digitalarticle tail -f /var/log/supervisor/nginx.log

# Error logs
docker exec digitalarticle tail -f /var/log/supervisor/backend_err.log
```

### Stop/Start/Restart

```bash
docker stop digitalarticle     # Stop container (volumes persist)
docker start digitalarticle    # Start stopped container
docker restart digitalarticle  # Restart running container
```

### Backup Volumes

```bash
# Backup notebooks
docker run --rm \
  -v digitalarticle-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/notebooks-backup.tar.gz -C /data/notebooks .

# Backup models
docker run --rm \
  -v digitalarticle-models:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/models-backup.tar.gz -C /data .
```

---

## Docker Compose Alternative

Create `docker-compose-unified.yml`:

```yaml
version: '3.8'

services:
  digitalarticle:
    build:
      context: ..
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

volumes:
  digitalarticle-data:
  digitalarticle-models:
```

Run with:
```bash
docker compose -f docker-compose-unified.yml up -d --build
```

---

## Troubleshooting

### Build Fails: "COPY failed"

**Problem**: Docker can't find `frontend/`, `backend/`, or `config.json`

**Solution**: Must build from project root
```bash
cd /path/to/DigitalArticle  # Go to project root
ls config.json              # Verify this file exists
docker build -f docker/Dockerfile.unified -t digitalarticle:unified .
```

### Model Downloads Every Time

**Problem**: Model re-downloads on each container restart

**Solution**: Verify volume mounted correctly
```bash
# Check volume exists
docker volume ls | grep digitalarticle-models

# Check volume is mounted
docker inspect digitalarticle | grep -A 5 Mounts

# Verify model in volume
docker exec digitalarticle ls -la /models/manifests
```

### Frontend Returns 502

**Problem**: Nginx can't reach backend

**Solution**: Check backend service
```bash
# Check backend running
docker exec digitalarticle supervisorctl status backend

# Check backend logs
docker exec digitalarticle tail -50 /var/log/supervisor/backend_err.log

# Restart backend
docker exec digitalarticle supervisorctl restart backend
```

### Out of Memory

**Problem**: Container crashes during LLM inference

**Solution**: Increase memory limit
```bash
docker run -d \
  --name digitalarticle \
  -p 80:80 \
  --memory=36g \
  --memory-reservation=8g \
  -v digitalarticle-data:/app/data \
  -v digitalarticle-models:/models \
  digitalarticle:unified
```

### Services Won't Start

**Problem**: supervisorctl shows FATAL state

**Solution**: Check individual service logs
```bash
# Check which service failed
docker exec digitalarticle supervisorctl status

# View error logs
docker exec digitalarticle cat /var/log/supervisor/ollama_err.log
docker exec digitalarticle cat /var/log/supervisor/backend_err.log
docker exec digitalarticle cat /var/log/supervisor/nginx_err.log
```

---

## Production Deployment

### Resource Limits

```bash
docker run -d \
  --name digitalarticle \
  -p 80:80 \
  --cpus=10 \
  --memory=36g \
  --memory-reservation=8g \
  -v digitalarticle-data:/app/data \
  -v digitalarticle-models:/models \
  --restart unless-stopped \
  digitalarticle:unified
```

### Behind Reverse Proxy (HTTPS)

Example nginx config on host:

```nginx
server {
    listen 443 ssl http2;
    server_name digitalarticle.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Then run container on different port:
```bash
docker run -d --name digitalarticle -p 8080:80 \
  -v digitalarticle-data:/app/data \
  -v digitalarticle-models:/models \
  -e CORS_ORIGINS=https://digitalarticle.example.com \
  digitalarticle:unified
```

---

## Comparison: Unified vs Multi-Container

| Aspect | Unified Image | Multi-Container |
|--------|---------------|-----------------|
| **Deployment** | Single `docker run` | `docker compose up` |
| **Containers** | 1 | 3 (ollama, backend, frontend) |
| **Networking** | Localhost (faster) | Docker network |
| **Complexity** | Lower | Higher |
| **Scalability** | Limited | Better (scale services independently) |
| **Best For** | Simple deployments, platforms with 1-image limit | Production, multi-instance deployments |

---

## Additional Documentation

- **Complete Deployment Guide**: [`../docs/DOCKER-DEPLOYMENT.md`](../docs/DOCKER-DEPLOYMENT.md)
- **Implementation Details**: [`../docs/devnotes/docker-one-image.md`](../docs/devnotes/docker-one-image.md)
- **Multi-Container Setup**: [`readme-multi-container.md`](readme-multi-container.md)

---

## Support

**Issues?** Check the troubleshooting section above or see the complete guide at [`../docs/DOCKER-DEPLOYMENT.md`](../docs/DOCKER-DEPLOYMENT.md)

**Branch**: `docker-onefile`
**Last Updated**: 2025-11-25
**Status**: Production Ready ✅
