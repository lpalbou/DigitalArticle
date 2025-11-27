# Digital Article Docker Configuration

This directory contains Docker configurations for deploying Digital Article. We offer two deployment strategies: **Monolithic** (Single Container) and **3-Tier** (Microservices).

## 📂 Directory Structure

```
docker/
├── monolithic/       # All-in-One Images (Best for simple deployment)
│   ├── Dockerfile          # Standard/CPU Image
│   ├── Dockerfile.apple    # Optimized for Apple Silicon
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

