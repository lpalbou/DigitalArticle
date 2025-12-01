# Digital Article - Docker Containerization Guide

> **📋 Looking for deployment instructions?** See:
> - [`docker/README.md`](../docker/README.md) - Overview and which option to choose
> - [`docker/monolithic/README.md`](../docker/monolithic/README.md) - Single container deployment
> - [`docker/3-tiers/README.md`](../docker/3-tiers/README.md) - Multi-container deployment

This document explains the **architecture and design decisions** behind Digital Article's containerization. It's intended for developers who want to understand the system internals, not for end-user deployment.

## 📐 Architecture Overview

### Component Separation

Digital Article uses a **microservices architecture** with three independent containers:

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Network (Bridge)                   │
│                                                               │
│  ┌──────────────┐      ┌────────────────┐      ┌─────────┐ │
│  │   Frontend   │─────→│    Backend     │─────→│ Ollama  │ │
│  │              │      │                │      │         │ │
│  │ Nginx        │      │ FastAPI        │      │ LLM     │ │
│  │ + React SPA  │      │ + Python       │      │ Service │ │
│  └──────┬───────┘      └────────┬───────┘      └────┬────┘ │
│         │                       │                    │      │
│    Port 80                 Port 8000            Port 11434  │
│         │                       │                    │      │
└─────────┼───────────────────────┼────────────────────┼──────┘
          ↓                       ↓                    ↓
      User Access            API Access          LLM API Access
   http://localhost      http://localhost:8000  http://localhost:11434
```

### Why Three Separate Containers?

#### 1. **Frontend Container (Nginx + React)**

**Purpose**: Serves the user interface and acts as reverse proxy

**Technology Stack**:
- **Nginx Alpine** (~25MB) - Production web server
- **React 18** - Built as static files (HTML, CSS, JS)
- **Vite** - Used during build, not in container

**Why Separate?**
- ✅ **Performance**: Nginx is 10x faster than Node for static files
- ✅ **Size**: 25MB vs 400MB+ with Node
- ✅ **Scaling**: Can scale frontend independently
- ✅ **Security**: No Node runtime vulnerabilities in production

**What It Does**:
- Serves React SPA from `/usr/share/nginx/html`
- Proxies API calls (`/api/*`) to backend container
- Provides health check endpoint (`/health`)
- Handles gzip compression and caching

**Build Process**:
```dockerfile
# Stage 1: Build React app with Node
FROM node:20-alpine AS builder
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci  # Install all dependencies (including dev for build)
COPY frontend/ .
RUN npm run build  # Creates dist/ folder

# Stage 2: Serve with Nginx
FROM nginx:alpine
COPY --from=builder /build/dist /usr/share/nginx/html
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
```

**Why Multi-Stage?**
- Build artifacts (node_modules, TypeScript) aren't in final image
- Final image is ~25MB instead of ~400MB
- Faster deployment and startup

---

#### 2. **Backend Container (FastAPI + Python)**

**Purpose**: API server, code generation, and code execution

**Technology Stack**:
- **Python 3.12 Slim** (~800MB with dependencies)
- **FastAPI** - REST API framework
- **AbstractCore** - LLM provider abstraction
- **Scientific Libraries** - pandas, numpy, matplotlib, scipy, sklearn

**Why Separate?**
- ✅ **Isolation**: Code execution isolated from frontend
- ✅ **Resources**: Can allocate more memory/CPU
- ✅ **Security**: Sandboxed code execution
- ✅ **Scaling**: Can run multiple backend instances

**What It Does**:
- Exposes REST API at `/api/*` endpoints
- Generates Python code from natural language prompts (via LLM)
- Executes generated code in isolated namespace
- Captures results (plots, tables, stdout/stderr)
- Stores notebooks as JSON files
- Communicates with Ollama for LLM inference

**Build Process**:
```dockerfile
# Stage 1: Build dependencies
FROM python:3.12-slim AS builder
RUN apt-get update && apt-get install -y gcc g++ libpq-dev
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim
RUN apt-get update && apt-get install -y libpq-dev curl
RUN useradd -m -u 1000 appuser  # Non-root user
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /app
COPY backend/ ./backend/
COPY pyproject.toml config.json .
USER appuser  # Security: run as non-root
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Why Multi-Stage?**
- Build tools (gcc, g++) not in production image
- Reduces attack surface
- Faster image pulls and deployments
- Final size: ~800MB vs ~1.2GB single-stage

**Environment Variables**:
- `OLLAMA_BASE_URL`: URL of Ollama service (e.g., `http://ollama:11434`)
- `CORS_ORIGINS`: Allowed origins for API calls
- `LOG_LEVEL`: Logging verbosity (INFO, DEBUG, ERROR)
- `PYTHONUNBUFFERED`: Real-time log output

---

#### 3. **Ollama Container (LLM Service)**

**Purpose**: Local Large Language Model inference

**Technology Stack**:
- **Ollama** - LLM runtime (official image)
- **qwen3-coder:30b** - Code generation model (~17GB)

**Why Separate?**
- ✅ **Resources**: LLM needs 16-32GB RAM independently
- ✅ **GPU Support**: Can enable GPU without affecting other services
- ✅ **Lifecycle**: Model updates don't require backend rebuild
- ✅ **Reusability**: Other applications can use same Ollama instance

**What It Does**:
- Runs LLM inference locally (no external API calls)
- Exposes OpenAI-compatible API at port 11434
- Manages model storage (17GB+ per model)
- Handles concurrent inference requests

**Configuration**:
```yaml
ollama:
  image: ollama/ollama:latest  # Official image
  ports:
    - "11434:11434"
  volumes:
    - ollama-models:/root/.ollama  # Persistent model storage
  # Optional GPU support (requires nvidia-docker):
  # deploy:
  #   resources:
  #     reservations:
  #       devices:
  #         - driver: nvidia
  #           count: all
  #           capabilities: [gpu]
```

**Model Storage**:
- Named volume `ollama-models` persists across restarts
- First download: 10-30 minutes (17GB)
- Subsequent starts: Instant (model cached)

---

### Container Communication

#### Service Discovery

Containers communicate using **Docker service names** as hostnames:

```python
# Backend connects to Ollama
ollama_url = os.getenv('OLLAMA_BASE_URL', 'http://ollama:11434')
#                                                   ^^^^^^
#                                             Service name, not IP!
```

#### Network Configuration

All services on same bridge network (`digitalarticle-network`):

```yaml
networks:
  digitalarticle-network:
    name: digitalarticle-network
    driver: bridge
```

**Benefits**:
- Automatic DNS resolution (service names → IP addresses)
- Isolated from other Docker networks
- No port conflicts with host

#### Request Flow

1. **User → Frontend (Nginx)**:
   ```
   http://localhost → Nginx (port 80) → React SPA
   ```

2. **Frontend → Backend**:
   ```
   http://localhost/api/notebooks
   → Nginx reverse proxy
   → http://backend:8000/api/notebooks
   ```

3. **Backend → Ollama**:
   ```
   Python code: ollama_url = "http://ollama:11434"
   → Docker network DNS
   → Ollama container on port 11434
   ```

---

### Data Persistence

#### Volume Types

**Named Volumes** (managed by Docker):
```yaml
volumes:
  ollama-models:
    name: digitalarticle-ollama-models
  backend-logs:
    name: digitalarticle-logs
```

**Bind Mounts** (direct host directory mapping):
```yaml
volumes:
  - ./notebooks:/app/notebooks       # Notebook JSON files
  - ./data:/app/data                 # Uploaded data files
  - ./sample_data:/app/sample_data   # Sample datasets
  - ./config.json:/app/config.json   # LLM configuration
```

#### Why Bind Mounts for Notebooks?

✅ **Transparency**: Direct access to `.json` files on host
✅ **Git-Friendly**: Can version control notebooks
✅ **Backup**: Simple `tar -czf backup.tar.gz notebooks/`
✅ **Debugging**: Open files in editor while container runs

#### Why Named Volume for Models?

✅ **Performance**: Docker-optimized storage
✅ **Portability**: Can move between Docker hosts
✅ **Size**: 17GB+ doesn't clutter project directory
✅ **Lifecycle**: Persists even if container deleted

---

## 🚀 Deployment Methods

### Method 1: Docker CLI (Command Line)

#### Prerequisites

- Docker 20.10+ installed
- Docker Compose v2 (or `docker-compose` v1.29+)
- 16-32GB RAM available
- 25GB free disk space

#### Installation Steps

**Step 1: Clone Repository**
```bash
git clone https://github.com/lpalbou/DigitalArticle.git
cd DigitalArticle
```

**Step 2: Create Required Directories**
```bash
mkdir -p notebooks
```

**Step 3: Build Images**
```bash
# Build all three services
docker-compose build

# View built images
docker images | grep digitalarticle
```

Expected output:
```
digitalarticle-backend    latest   abc123   800MB
digitalarticle-frontend   latest   def456    25MB
ollama/ollama            latest   ghi789     2GB
```

**Step 4: Start Services**
```bash
# Start all services in detached mode
docker-compose up -d

# View running containers
docker-compose ps
```

Expected output:
```
NAME                      STATUS          PORTS
digitalarticle-backend    Up (healthy)    0.0.0.0:8000->8000/tcp
digitalarticle-frontend   Up (healthy)    0.0.0.0:80->80/tcp
digitalarticle-ollama     Up (healthy)    0.0.0.0:11434->11434/tcp
```

**Step 5: Monitor Model Download**

The Ollama container automatically pulls the model configured in `config.json` via the ollama-entrypoint.sh script. Model downloads in the background (10-30 minutes for qwen3-coder:30b).

```bash
# Watch Ollama download progress
docker-compose logs -f ollama
```

Progress output:
```
digitalarticle-ollama | Starting Ollama service...
digitalarticle-ollama | Pulling model: qwen3-coder:30b
digitalarticle-ollama | pulling manifest
digitalarticle-ollama | pulling 4039454a552d... 17.2 GB ██████████ 45%
```

**Step 6: Verify Deployment**
```bash
# Check health status
docker-compose ps

# Test frontend
curl http://localhost/health
# Expected: healthy

# Test backend
curl http://localhost:8000/health
# Expected: {"status":"healthy"}

# Test Ollama
curl http://localhost:11434/api/tags
# Expected: JSON with model list including qwen3-coder:30b
```

**Step 7: Access Application**
```bash
# Linux/macOS
open http://localhost

# Windows
start http://localhost
```

#### Common CLI Commands

**View Logs**:
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend

# Last 100 lines
docker-compose logs --tail=100 backend

# Since specific time
docker-compose logs --since 30m backend
```

**Stop Services**:
```bash
# Stop all services (keep volumes)
docker-compose down

# Stop and remove volumes (⚠️ deletes notebooks!)
docker-compose down -v

# Stop specific service
docker-compose stop backend
```

**Restart Services**:
```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart backend
```

**Update After Code Changes**:
```bash
# Rebuild specific service
docker-compose build backend

# Rebuild and restart
docker-compose up -d --build backend

# Force complete rebuild (no cache)
docker-compose build --no-cache
```

**Execute Commands in Container**:
```bash
# Backend container
docker-compose exec backend bash

# Check Python packages
docker-compose exec backend pip list

# Ollama container
docker-compose exec ollama ollama list
```

**View Resource Usage**:
```bash
# Real-time stats
docker stats

# One-time snapshot
docker stats --no-stream
```

---

### Method 2: Docker Desktop (GUI)

Docker Desktop provides a visual interface for managing containers. Available for macOS and Windows.

#### Installation

1. **Download Docker Desktop**:
   - macOS: https://docs.docker.com/desktop/install/mac-install/
   - Windows: https://docs.docker.com/desktop/install/windows-install/

2. **Install and Launch**:
   - Run installer
   - Launch Docker Desktop
   - Wait for "Docker is running" status (green indicator)

3. **Verify Installation**:
   - Open terminal/command prompt
   - Run: `docker --version`
   - Expected: `Docker version 24.0.0` or higher

#### Using Docker Desktop

**Step 1: Open Terminal in Project Directory**
```bash
cd path/to/DigitalArticle
```

**Step 2: Build and Start with Docker Desktop**

**Option A: Use GUI**:

1. Open Docker Desktop application
2. Go to **Images** tab
3. Click **Build** button
4. Select `docker-compose.yml` from your project
5. Click **Run**

**Option B: Use Integrated Terminal** (Recommended):

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d
```

**Step 3: Monitor Services in GUI**

1. **Containers Tab**:
   - View all running containers
   - See status (running, healthy, exited)
   - View resource usage (CPU, memory)

2. **Container Actions** (right-click on container):
   - **View Logs**: Real-time log streaming
   - **Inspect**: View detailed configuration
   - **Terminal**: Open shell inside container
   - **Stop/Restart**: Control container lifecycle
   - **Delete**: Remove container

3. **Status Indicators**:
   - 🟢 Green: Running and healthy
   - 🟡 Yellow: Starting or unhealthy
   - 🔴 Red: Stopped or error

**Step 4: View Logs via GUI**

1. Click on container name (e.g., `digitalarticle-backend`)
2. Click **Logs** tab
3. Logs update in real-time
4. Use search box to filter logs
5. Click **Copy** to copy logs to clipboard

**Step 5: Monitor Ollama Model Download**

The Ollama container automatically downloads the model from `config.json` via ollama-entrypoint.sh. Monitor progress:

```bash
# Watch model download progress
docker-compose logs -f ollama

# Or check if model is loaded
docker exec digitalarticle-ollama ollama list
```

**Step 6: Access Application**

1. In **Containers** tab, find `digitalarticle-frontend`
2. Click **Open in Browser** icon next to port 80
3. Or manually open: http://localhost

#### Docker Desktop Features

**1. Volume Management**:
- Go to **Volumes** tab
- See `digitalarticle-ollama-models` (17GB+)
- See `digitalarticle-logs`
- Right-click → **Inspect** to see mount point
- Right-click → **Delete** to remove (⚠️ model will need re-download)

**2. Network Inspection**:
- Go to **Networks** tab
- Find `digitalarticle-network`
- Click to see connected containers
- View IP addresses assigned

**3. Resource Limits**:
- Click **Settings** (gear icon)
- Go to **Resources**
- Set:
  - **CPUs**: 4+ recommended
  - **Memory**: 24GB+ for qwen3-coder:30b
  - **Disk**: 50GB+ recommended

**4. Cleanup**:
- Go to **Containers** tab
- Select `digitalarticle-*` containers
- Right-click → **Delete** (removes containers)
- Go to **Images** tab
- Select `digitalarticle-*` images
- Right-click → **Delete** (removes images)
- Go to **Volumes** tab
- Select volumes → Delete (⚠️ removes model)

**5. Troubleshooting**:
- **View Logs**: Click container → Logs tab
- **Inspect Container**: Click container → Inspect tab
- **Terminal Access**: Click container → Terminal tab
- **Restart**: Right-click container → Restart

---

## 🔧 Configuration

### Environment Variables

Edit `docker-compose.yml` to customize:

```yaml
backend:
  environment:
    # Ollama URL (don't change unless using external Ollama)
    - OLLAMA_BASE_URL=http://ollama:11434

    # Real-time log output (always on)
    - PYTHONUNBUFFERED=1

    # Logging verbosity: INFO, DEBUG, WARNING, ERROR
    - LOG_LEVEL=INFO

    # CORS origins for API access
    # "*" = Allow all origins (development/testing)
    # For production: set to your domain(s), comma-separated
    - CORS_ORIGINS=*
    # - CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

**For Remote Deployment**:

If deploying to a remote server at `https://yourdomain.com`, update:

```yaml
backend:
  environment:
    - CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

Or keep `CORS_ORIGINS=*` for development (allows any origin)

### LLM Configuration

Edit `config.json` to change model:

```json
{
  "llm": {
    "provider": "ollama",
    "model": "qwen3-coder:30b"
  }
}
```

**Available Models**:
- `qwen3-coder:30b` - Best quality, 17GB, requires 16-32GB RAM
- `qwen3-coder:7b` - Faster, 4GB, requires 8-16GB RAM
- `codellama:34b` - Alternative, 19GB
- `deepseek-coder:33b` - Alternative, 18GB

To change model:
```bash
# Pull new model
docker exec digitalarticle-ollama ollama pull qwen3-coder:7b

# Update config.json
# Restart backend
docker-compose restart backend
```

### Port Configuration

To use different ports, edit `docker-compose.yml`:

```yaml
frontend:
  ports:
    - "8080:80"  # Access at http://localhost:8080

backend:
  ports:
    - "9000:8000"  # Access at http://localhost:9000

ollama:
  ports:
    - "12434:11434"  # Access at http://localhost:12434
```

**Remember**: Update `OLLAMA_BASE_URL` if changing Ollama port.

---

## 🐛 Troubleshooting

### Issue: Frontend Build Fails

**Error**:
```
sh: 1: tsc: not found
ERROR: failed to solve: process "/bin/sh -c npm run build" did not complete
```

**Cause**: Missing devDependencies (TypeScript, Vite)

**Fix**: Ensure `docker/Dockerfile.frontend` line 11 is:
```dockerfile
RUN npm ci  # NOT: RUN npm ci --only=production
```

---

### Issue: Backend Can't Connect to Ollama

**Error in logs**:
```
Failed to initialize LLM: Could not connect to http://ollama:11434
```

**Cause**: Ollama not healthy yet

**Fix**:
```bash
# Check Ollama health
docker-compose ps ollama

# View Ollama logs
docker-compose logs ollama

# Wait for health check (120s start period)
docker-compose up -d
sleep 120
docker-compose ps
```

---

### Issue: Permission Denied on Notebooks

**Error**:
```
PermissionError: [Errno 13] Permission denied: '/app/notebooks/abc123.json'
```

**Cause**: `notebooks/` directory owned by root

**Fix**:
```bash
# Delete container and volumes
docker-compose down -v

# Create directory with correct permissions
mkdir -p notebooks
chmod 755 notebooks

# Restart
docker-compose up -d
```

---

### Issue: Model Download Slow/Timeout

**Symptom**: Model download hangs at 10% for 30+ minutes

**Cause**: Slow internet connection (17GB download)

**Fix Option 1**: Use smaller model
```bash
docker exec digitalarticle-ollama ollama pull qwen3-coder:7b  # 4GB instead of 17GB
# Update config.json
```

**Fix Option 2**: Resume download
```bash
# If interrupted, Ollama automatically resumes on container restart
docker-compose restart ollama
docker-compose logs -f ollama  # Monitor progress
```

---

### Issue: Out of Memory

**Error**:
```
docker: Error response from daemon: OOM command not allowed when used memory > 'maxmemory'
```

**Cause**: Insufficient RAM for qwen3-coder:30b

**Fix**:
```bash
# Option 1: Increase Docker memory limit
# Docker Desktop → Settings → Resources → Memory: 24GB+

# Option 2: Use smaller model
docker exec digitalarticle-ollama ollama pull qwen3-coder:7b
```

---

## 📊 Performance Tuning

### Resource Allocation

**Recommended Settings** (Docker Desktop → Settings → Resources):
- **CPUs**: 4-8 cores
- **Memory**: 24-32GB (for 30B model)
- **Swap**: 2GB
- **Disk**: 50GB+

### Image Size Optimization

Current sizes:
- Backend: ~800MB ✓ (optimized with multi-stage)
- Frontend: ~25MB ✓ (optimized with Nginx)
- Ollama: ~2GB (official image)

**If need smaller**:
- Use `python:3.12-alpine` for backend (-300MB)
- Remove unused Python packages from requirements.txt

### Startup Time

Expected times:
- Ollama: 30s (model not loaded)
- Backend: 15s (health check passes)
- Frontend: 5s (Nginx starts instantly)
- **Total**: ~60s for all services healthy

**First Model Use**: +30-60s (model loads into RAM)

### Model Warm-Up

To pre-load the model into memory for faster first use:
```bash
# Pre-loads model into memory
docker exec digitalarticle-ollama ollama run qwen3-coder:30b "print('Hello')"
```

Benefits:
- First code generation is fast (no 60s delay)
- Subsequent generations are instant

**Note**: The ollama-entrypoint.sh script automatically pulls the model from `config.json` on container startup.

---

## 🔐 Security Considerations

### Current Security Features

✅ **Non-root users**: Containers run as uid 1000 (appuser)
✅ **Minimal images**: Slim/Alpine base images
✅ **Network isolation**: Bridge network, not host network
✅ **No privileged mode**: Containers can't access host directly
✅ **Health checks**: Detect compromised services
✅ **Security headers**: Nginx adds X-Frame-Options, etc.

### Current Limitations (POC)

⚠️ **Code execution not sandboxed**: Generated code runs in backend container
⚠️ **No authentication**: Anyone with network access can use
⚠️ **HTTP only**: No HTTPS/SSL encryption
⚠️ **CORS permissive**: Allows localhost origins

### Production Recommendations

For production deployment:

1. **Add SSL/TLS**:
   ```bash
   # Use Let's Encrypt + Certbot
   docker-compose exec frontend certbot --nginx
   ```

2. **Restrict CORS**:
   ```yaml
   # Only allow production domain
   CORS_ORIGINS=https://yourdomain.com
   ```

3. **Add Authentication**:
   - Implement OAuth2/JWT
   - Use Nginx basic auth as interim

4. **Sandbox Code Execution**:
   - Use Docker-in-Docker for user code
   - Or use serverless functions (AWS Lambda, etc.)

5. **Enable Firewall**:
   ```bash
   # Only expose port 80/443
   frontend:
     ports:
       - "80:80"
   # Remove backend and ollama port exposure
   ```

---

## 📚 Additional Resources

- **Docker Documentation**: https://docs.docker.com/
- **Docker Compose**: https://docs.docker.com/compose/
- **Docker Desktop**: https://www.docker.com/products/docker-desktop/
- **Ollama**: https://ollama.ai/
- **Nginx**: https://nginx.org/en/docs/
- **FastAPI**: https://fastapi.tiangolo.com/

---

## 🆘 Getting Help

If you encounter issues:

1. **Check logs**:
   ```bash
   docker-compose logs -f
   ```

2. **Verify system requirements**:
   - 16GB+ RAM
   - 25GB+ disk space
   - Docker 20.10+

3. **Review troubleshooting section** above

4. **Open GitHub issue** with:
   - `docker-compose logs` output
   - `docker-compose ps` output
   - System specs (RAM, Docker version)
   - Steps to reproduce

---

**Last Updated**: 2025-11-20
**Docker Version**: 20.10+
**Compose Version**: v2 (or v1.29+)
