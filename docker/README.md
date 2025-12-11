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

## 🤖 LLM Provider Configuration

The Docker containers support multiple LLM providers. Configuration is done via environment variables (following Docker conventions).

### Supported Providers

| Provider | Type | Status | Notes |
|----------|------|--------|-------|
| `ollama` | Local (bundled) | ✅ Included | Default. Binary bundled in container. |
| `openai` | Cloud API | ✅ Included | Requires `OPENAI_API_KEY` |
| `anthropic` | Cloud API | ✅ Included | Requires `ANTHROPIC_API_KEY` |
| `lmstudio` | External server | ✅ Included | Desktop app on host, use `LMSTUDIO_BASE_URL` |
| `huggingface` | Local inference | ✅ Included | Runs models locally with torch/transformers |
| `vllm` | External GPU server | ✅ Included | High-throughput inference, use `VLLM_BASE_URL` |
| `openai-compatible` | External server | ✅ Included | Any OpenAI-compatible API, use `OPENAI_COMPATIBLE_BASE_URL` |

### Quick Examples

```bash
# Default: Ollama (bundled)
docker run -p 80:80 -v data:/app/data digital-article:unified

# OpenAI
docker run -p 80:80 -v data:/app/data \
    -e LLM_PROVIDER=openai \
    -e LLM_MODEL=gpt-4o \
    -e OPENAI_API_KEY=sk-... \
    digital-article:unified

# Anthropic
docker run -p 80:80 -v data:/app/data \
    -e LLM_PROVIDER=anthropic \
    -e LLM_MODEL=claude-3-5-sonnet-latest \
    -e ANTHROPIC_API_KEY=sk-ant-... \
    digital-article:unified

# LMStudio (external server on host)
docker run -p 80:80 -v data:/app/data \
    -e LLM_PROVIDER=lmstudio \
    -e LLM_MODEL=qwen/qwen3-32b \
    -e LMSTUDIO_BASE_URL=http://host.docker.internal:1234/v1 \
    digital-article:unified

# vLLM (high-throughput GPU inference - NVIDIA CUDA only)
docker run -p 80:80 -v data:/app/data \
    -e LLM_PROVIDER=vllm \
    -e LLM_MODEL=Qwen/Qwen2.5-Coder-7B-Instruct \
    -e VLLM_BASE_URL=http://host.docker.internal:8000/v1 \
    digital-article:unified

# OpenAI-Compatible (llama.cpp, text-generation-webui, LocalAI, etc.)
docker run -p 80:80 -v data:/app/data \
    -e LLM_PROVIDER=openai-compatible \
    -e LLM_MODEL=my-local-model \
    -e OPENAI_COMPATIBLE_BASE_URL=http://host.docker.internal:8080/v1 \
    digital-article:unified
```

**Note:** When using external providers (openai, anthropic, lmstudio, huggingface, vllm, openai-compatible), the bundled Ollama server is not started, saving system resources.

See [monolithic/README.md](./monolithic/README.md) for complete configuration options.

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

