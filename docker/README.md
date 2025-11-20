# Digital Article - Docker Deployment Guide

This guide explains how to deploy Digital Article using Docker containers with Ollama LLM support.

## 📋 Prerequisites

### System Requirements
- **Memory**: 16-32GB RAM (for qwen3-coder:30b model)
- **Disk Space**: 25GB minimum
  - Backend image: ~800MB
  - Frontend image: ~25MB
  - Ollama image: ~2GB
  - qwen3-coder:30b model: ~17GB
- **Docker**: Version 20.10+ with Docker Compose v2
- **Internet**: For model download (first-time setup)

### Install Docker
```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER  # Add user to docker group
newgrp docker  # Refresh group membership

# macOS
# Install Docker Desktop from https://www.docker.com/products/docker-desktop
```

## 🚀 Quick Start

### Quick Test (skip 17GB model download)

```bash
# Build and start frontend/backend only (~2 minutes)
docker-compose build frontend backend
docker-compose up -d frontend backend

# Test UI and API at http://localhost
```

### Full Deployment (with LLM)

```bash
# Build all images (5-10 minutes)
docker-compose build

# Start all services
docker-compose up -d

# Pull qwen3-coder:30b model (10-30 minutes)
./docker/init-ollama.sh

# Access application
open http://localhost
```

### Quick Test (without LLM model)

For testing frontend/backend infrastructure only (skip 17GB model download):

```bash
# Build only frontend and backend
docker-compose build frontend backend

# Start without Ollama
docker-compose up -d frontend backend

# Access application (LLM won't work but UI/API will)
open http://localhost
```

**Note**: Code generation will fail without Ollama, but you can test UI, API, and infrastructure.

### Expected Output

```bash
docker-compose ps

NAME                        STATUS          PORTS
digitalarticle-backend      Up (healthy)    0.0.0.0:8000->8000/tcp
digitalarticle-frontend     Up (healthy)    0.0.0.0:80->80/tcp
digitalarticle-ollama       Up (healthy)    0.0.0.0:11434->11434/tcp  # Only if started
```

### Access Points
- **Web UI**: http://localhost
- **Backend API**: http://localhost:8000/docs (Swagger UI)
- **Ollama API**: http://localhost:11434/api/tags (if running)

## 📦 Architecture

```
┌───────────────────────────────────────────────┐
│          Docker Network (bridge)               │
│                                                 │
│  ┌──────────┐    ┌──────────┐    ┌─────────┐ │
│  │ Frontend │────│ Backend  │────│ Ollama  │ │
│  │ (Nginx)  │    │ (FastAPI)│    │ (LLM)   │ │
│  └─────┬────┘    └─────┬────┘    └────┬────┘ │
│        │               │               │      │
│   Port 80         Port 8000      Port 11434  │
└───────┼───────────────┼───────────────┼──────┘
        │               │               │
   http://localhost   (API)      (Direct LLM)
```

### Services

1. **Frontend (Nginx + React)**
   - Serves React SPA
   - Proxies `/api/*` to backend
   - Gzip compression, caching
   - Port: 80

2. **Backend (FastAPI + Python)**
   - REST API for notebooks
   - Code generation with LLM
   - Code execution sandbox
   - Port: 8000

3. **Ollama (LLM Service)**
   - Local LLM runtime
   - OpenAI-compatible API
   - Model: qwen3-coder:30b
   - Port: 11434

## 🛠️ Commands

### Start Services
```bash
# Start all services (detached)
docker-compose up -d

# Start with logs
docker-compose up

# Start specific service
docker-compose up -d backend
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend

# Last 100 lines
docker-compose logs --tail=100 backend
```

### Stop Services
```bash
# Stop all services
docker-compose down

# Stop and remove volumes (⚠️ deletes notebooks!)
docker-compose down -v
```

### Restart Services
```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart backend
```

### Rebuild After Changes
```bash
# Rebuild specific service
docker-compose build backend

# Rebuild and restart
docker-compose up -d --build backend
```

## 📂 Data Persistence

### Volumes

| Volume/Mount | Type | Purpose | Location |
|--------------|------|---------|----------|
| `./notebooks` | Bind mount | User notebooks | Project root |
| `./data` | Bind mount | Uploaded data | Project root |
| `./config.json` | Bind mount | LLM config | Project root |
| `ollama-models` | Named volume | LLM models | Docker volume |
| `backend-logs` | Named volume | Application logs | Docker volume |

### Backup Data
```bash
# Backup notebooks and data
tar -czf backup-$(date +%Y%m%d).tar.gz notebooks/ data/ config.json

# Restore
tar -xzf backup-20231120.tar.gz
```

## 🔧 Configuration

### LLM Provider (config.json)
```json
{
  "llm": {
    "provider": "ollama",
    "model": "qwen3-coder:30b"
  }
}
```

Change model:
```json
{
  "llm": {
    "provider": "ollama",
    "model": "qwen3-coder:7b"
  }
}
```

### Environment Variables

Edit `docker-compose.yml`:
```yaml
backend:
  environment:
    - OLLAMA_BASE_URL=http://ollama:11434
    - LOG_LEVEL=DEBUG  # INFO (default), DEBUG, WARNING, ERROR
    - PYTHONUNBUFFERED=1
```

### Port Mapping

To use different ports, edit `docker-compose.yml`:
```yaml
frontend:
  ports:
    - "8080:80"  # Access at http://localhost:8080

backend:
  ports:
    - "9000:8000"  # Access at http://localhost:9000
```

## 🐛 Troubleshooting

### Service Won't Start

**Check logs**:
```bash
docker-compose logs backend
```

**Common issues**:
1. **Port already in use**:
   ```bash
   # Find process using port 8000
   sudo lsof -i :8000
   # Kill process or change port in docker-compose.yml
   ```

2. **Insufficient memory**:
   ```bash
   # Check Docker memory limit
   docker system info | grep Memory
   # Increase in Docker Desktop settings (macOS/Windows)
   ```

3. **Permission denied**:
   ```bash
   sudo chown -R $(id -u):$(id -g) notebooks/ data/
   ```

### Ollama Model Issues

**Model not loading**:
```bash
# Check Ollama logs
docker-compose logs ollama

# List available models
docker exec digitalarticle-ollama ollama list

# Pull model manually
docker exec digitalarticle-ollama ollama pull qwen3-coder:30b
```

**Model too large**:
```bash
# Use smaller model (4GB instead of 17GB)
docker exec digitalarticle-ollama ollama pull qwen3-coder:7b

# Update config.json
{
  "llm": {
    "provider": "ollama",
    "model": "qwen3-coder:7b"
  }
}

# Restart backend
docker-compose restart backend
```

### Backend Connection Issues

**Can't connect to Ollama**:
```bash
# Check network connectivity
docker-compose exec backend curl http://ollama:11434/api/tags

# Expected: JSON response with model list
```

**API errors**:
```bash
# Check backend health
curl http://localhost:8000/health

# Expected: {"status": "ok"}

# Check detailed logs
docker-compose logs -f backend
```

### Frontend Issues

**404 errors**:
- Clear browser cache (Ctrl+Shift+R)
- Check Nginx logs: `docker-compose logs frontend`

**API calls failing**:
- Verify backend is healthy: `curl http://localhost:8000/health`
- Check Nginx proxy config: `docker exec digitalarticle-frontend cat /etc/nginx/conf.d/default.conf`

## 🔍 Development Mode

For development with hot reload:

### Option 1: Run Frontend Locally
```bash
# Start backend + ollama only
docker-compose up -d backend ollama

# Run frontend with dev server
cd frontend
npm install
npm run dev

# Access at http://localhost:3000
```

### Option 2: Mount Source Code
Edit `docker-compose.yml`:
```yaml
backend:
  volumes:
    - ./backend:/app/backend  # Hot reload backend code
```

## 📊 Resource Monitoring

### Container Stats
```bash
# Real-time stats
docker stats

# Specific service
docker stats digitalarticle-backend
```

### Disk Usage
```bash
# Overall Docker usage
docker system df

# Volume sizes
docker volume ls
docker volume inspect digitalarticle-ollama-models
```

### Memory Usage
```bash
# Container memory
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}"
```

Expected memory usage:
- Frontend: ~10MB
- Backend: ~200MB (idle), ~500MB (processing)
- Ollama: ~4GB (idle), ~18GB+ (with 30B model loaded)

## 🚨 Production Deployment

For production use, consider:

1. **HTTPS/SSL**:
   - Use Let's Encrypt with Certbot
   - Add SSL configuration to Nginx

2. **Security**:
   - Remove debug ports (only expose 80/443)
   - Use secrets management for API keys
   - Enable firewall rules

3. **Monitoring**:
   - Add health check endpoints
   - Use Prometheus + Grafana
   - Set up log aggregation

4. **Scaling**:
   - Use Docker Swarm or Kubernetes
   - Separate LLM service to dedicated hardware
   - Add load balancer for multiple backend instances

## 📝 Additional Resources

- **Docker Docs**: https://docs.docker.com/
- **Docker Compose**: https://docs.docker.com/compose/
- **Ollama**: https://ollama.ai/
- **AbstractCore**: https://github.com/Abstract-Core/abstractcore

## 🆘 Support

If you encounter issues:

1. Check logs: `docker-compose logs -f`
2. Verify system requirements (16GB+ RAM)
3. Ensure Docker is updated (20.10+)
4. Review troubleshooting section above
5. Open an issue on GitHub with:
   - `docker-compose logs` output
   - `docker-compose ps` output
   - System specs (RAM, Docker version)

---

**Quick Reference**:
- Start: `docker-compose up -d`
- Stop: `docker-compose down`
- Logs: `docker-compose logs -f`
- Access: http://localhost
