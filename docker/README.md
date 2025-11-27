# Digital Article Docker Configuration

This directory contains Docker configurations for deploying Digital Article. We offer two deployment strategies: **Monolithic** (Single Container) and **3-Tier** (Microservices).

## 📂 Directory Structure

```
docker/
├── monolithic/       # All-in-One Images (Best for simple deployment)
│   ├── Dockerfile          # Standard/CPU Image
│   └── Dockerfile.nvidia   # Optimized for NVIDIA GPU
│
└── 3-tiers/          # Multi-Container Setup (Best for Dev/Prod)
    ├── Dockerfile.backend
    ├── Dockerfile.frontend
    └── (Config files for separated services)
```

## 🚀 Which one should I choose?

### Choose [Monolithic (Unified)](./monolithic/README.md) if:
*   You want the simplest possible deployment (`docker run ...`).
*   You are deploying to a PaaS that only accepts a single Dockerfile (e.g., Railway, Render).
*   You want to distribute the app as a single artifact.
*   **To use:** Copy the appropriate Dockerfile from `docker/monolithic/` to the root of your repo as `Dockerfile`.

### Choose [3-Tier Architecture](./3-tiers/README.md) if:
*   You are developing the application (separate logs/restarts are helpful).
*   You use `docker-compose` or Kubernetes.
*   You want to scale components independently (e.g., running Ollama on a separate GPU node).
*   **To use:** Run `docker compose up` from the project root.

## ⚠️ Important Note on Context

All Docker build commands must be run from the **project root directory**, not inside the `docker/` folder, because the build context requires access to `backend/`, `frontend/`, and `config.json` at the root.

**Correct:**
```bash
cd /path/to/digital-article
docker build -f docker/monolithic/Dockerfile .
```

**Incorrect:**
```bash
cd /path/to/digital-article/docker
docker build -f monolithic/Dockerfile .
```

## 🔗 External Ollama (Remote GPU)

By default, the monolithic images include Ollama running inside the container. However, you can point the container to an **external Ollama instance** for better performance or to leverage a remote GPU server.

Use the `OLLAMA_BASE_URL` environment variable:

```bash
# Use native Ollama on your Mac (recommended for Apple Silicon)
docker run -d --name digital-article -p 80:80 \
    -v digital-article-data:/app/data \
    -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
    digital-article:latest

# Use a remote GPU server
docker run -d --name digital-article -p 80:80 \
    -v digital-article-data:/app/data \
    -e OLLAMA_BASE_URL=http://192.168.1.100:11434 \
    digital-article:latest

# Use a cloud-hosted Ollama instance
docker run -d --name digital-article -p 80:80 \
    -v digital-article-data:/app/data \
    -e OLLAMA_BASE_URL=http://ollama.mycompany.com:11434 \
    digital-article:latest
```

**Notes:**
- `host.docker.internal` is Docker Desktop's special DNS to reach the host machine from inside a container.
- For remote servers, ensure Ollama is bound to `0.0.0.0` (not `127.0.0.1`) and the port is accessible through firewalls.
- This pattern allows running the lightweight frontend/backend anywhere while offloading GPU inference to a dedicated machine.

