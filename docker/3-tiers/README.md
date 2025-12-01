# Digital Article - 3-Tier Docker Deployment

This directory contains the files for a **Multi-Container** (Microservices) deployment. This is the recommended setup for production environments, development debugging, or when you want to scale services independently.

## Architecture

The application is split into 3 separate containers:

1.  **Frontend (`docker/3-tiers/Dockerfile.frontend`)**
    *   Nginx serving React static files.
    *   Proxies `/api` requests to the backend container.
    *   Exposed on Port 80.

2.  **Backend (`docker/3-tiers/Dockerfile.backend`)**
    *   Python FastAPI application.
    *   Handles business logic, file management, and orchestration.
    *   Internal Port: 8000.

3.  **Ollama (Official Image)**
    *   Runs the LLM inference.
    *   Internal Port: 11434.

## How to Run (Docker Compose)

The easiest way to run the 3-tier stack is using `docker-compose` from the project root.

### 1. Prerequisites
- Docker & Docker Compose installed.
- For GPU support: NVIDIA Container Toolkit installed.

### 2. Start Services

**Navigate to project root:**
```bash
cd /path/to/digital-article
```

**Run with Docker Compose:**
```bash
docker compose up --build
```

Access the application at `http://localhost`.

### 3. GPU Support (Optional)

To enable GPU support for Ollama in the 3-tier setup, uncomment the GPU section in `docker-compose.yml`:

```yaml
# In docker-compose.yml under 'ollama' service:
# deploy:
#   resources:
#     reservations:
#       devices:
#         - driver: nvidia
#           count: all
#           capabilities: [gpu]
```

## File Structure

*   `Dockerfile.backend`: Builds the Python API image.
*   `Dockerfile.frontend`: Builds the React/Nginx image.
*   `entrypoint.backend.sh`: Startup script for backend (waits for Ollama).
*   `entrypoint.ollama.sh`: Custom entrypoint for Ollama container.
*   `nginx.conf`: Nginx configuration for the Frontend container.

## Volumes

The 3-tier setup uses named volumes for persistence:

| Volume | Mount Point | Purpose |
|--------|-------------|---------|
| `notebooks-data` | `/app/notebooks` | Notebook files |
| `app-data` | `/app/data` | Workspace and user data |
| `ollama-models` | `/root/.ollama` | Ollama model cache |
| `huggingface-models` | `/models/huggingface` | HuggingFace model cache (`HF_HOME`) |

Models are cached in volumes to avoid re-downloading on container restart.

## Development

This setup is ideal for development because:
*   You can restart just the backend: `docker compose restart backend`
*   You can rebuild just the frontend: `docker compose build frontend && docker compose up -d frontend`
*   Logs are separated: `docker compose logs -f backend`
