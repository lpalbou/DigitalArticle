# Digital Article Docker Configuration

This directory contains Docker configurations for deploying Digital Article.

## 📂 Directory Structure

```
docker/
├── 2-tiers/          # DEFAULT: Frontend + Backend (external LLM)
│   ├── Dockerfile          # Lightweight, connects to host LLM servers
│   ├── nginx.conf
│   ├── supervisord.conf
│   └── entrypoint.sh
│
├── monolithic/       # All-in-One (bundled Ollama)
│   ├── Dockerfile          # Standard/CPU with bundled Ollama
│   └── Dockerfile.nvidia   # NVIDIA GPU optimized
│
└── 3-tiers/          # Microservices (docker-compose)
    ├── Dockerfile.backend
    ├── Dockerfile.frontend
    └── (Config files for separated services)

Dockerfile (root)     # Copy of 2-tiers for PaaS platforms
```

## 🚀 Quick Start

The **root Dockerfile** uses the 2-tiers configuration (external LLM):

```bash
# Build
docker build -t digital-article .

# Run (connects to LLM server on host:1234 by default)
docker run -p 80:80 -v da-data:/app/data digital-article
```

## 🤖 Default Configuration

| Setting | Default Value |
|---------|---------------|
| `LLM_PROVIDER` | `openai-compatible` |
| `LLM_MODEL` | *(empty - auto-detect)* |
| `OPENAI_COMPATIBLE_BASE_URL` | `http://host.docker.internal:1234/v1` |

The container connects to any OpenAI-compatible server (LMStudio, llama.cpp, vLLM, LocalAI, etc.) running on your host machine at port 1234.

## ⚙️ Configuration Methods

### Method 1: Runtime Environment Variables (-e)

```bash
# Custom URL and model
docker run -p 80:80 -v da-data:/app/data \
    -e OPENAI_COMPATIBLE_BASE_URL=http://host.docker.internal:8080/v1 \
    -e LLM_MODEL=my-model-name \
    digital-article

# Different port
docker run -p 80:80 -v da-data:/app/data \
    -e OPENAI_COMPATIBLE_BASE_URL=http://host.docker.internal:5000/v1 \
    digital-article
```

### Method 2: Build-Time Arguments (--build-arg)

```bash
# Bake configuration into image
docker build \
    --build-arg OPENAI_COMPATIBLE_BASE_URL=http://myserver:8080/v1 \
    --build-arg LLM_MODEL=qwen2.5-coder \
    -t digital-article:custom .
```

### Method 3: Different Provider

```bash
# Use Ollama instead
docker run -p 80:80 -v da-data:/app/data \
    -e LLM_PROVIDER=ollama \
    -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
    -e LLM_MODEL=gemma3n:e2b \
    digital-article

# Use OpenAI cloud
docker run -p 80:80 -v da-data:/app/data \
    -e LLM_PROVIDER=openai \
    -e LLM_MODEL=gpt-4o \
    -e OPENAI_API_KEY=sk-... \
    digital-article
```

## 🔌 Supported Providers

| Provider | Type | Default URL | Notes |
|----------|------|-------------|-------|
| `openai-compatible` | External | `host.docker.internal:1234/v1` | **Default**. LMStudio, llama.cpp, LocalAI, etc. |
| `ollama` | External | `host.docker.internal:11434` | Ollama on host |
| `lmstudio` | External | `host.docker.internal:1234/v1` | LMStudio desktop app |
| `vllm` | External | `host.docker.internal:8000/v1` | High-throughput GPU inference |
| `openai` | Cloud API | *(uses default)* | Requires `OPENAI_API_KEY` |
| `anthropic` | Cloud API | *(uses default)* | Requires `ANTHROPIC_API_KEY` |
| `huggingface` | Local | N/A | Runs models inside container |

## 📦 Image Variants

### 2-Tiers (Default) - `docker/2-tiers/`

- **Best for:** Most users, external LLM servers
- **Size:** ~500MB
- **Build time:** ~2 min
- **LLM:** Connects to external server (LMStudio, Ollama, vLLM, etc.)

```bash
docker build -f docker/2-tiers/Dockerfile -t digital-article:2tiers .
```

### Monolithic - `docker/monolithic/`

- **Best for:** Self-contained deployment, no external dependencies
- **Size:** ~2GB
- **Build time:** ~5 min
- **LLM:** Bundled Ollama binary

```bash
docker build -f docker/monolithic/Dockerfile -t digital-article:mono .
```

### NVIDIA GPU - `docker/monolithic/Dockerfile.nvidia`

- **Best for:** GPU-accelerated inference with NVIDIA CUDA
- **Requires:** NVIDIA Container Toolkit, `--gpus all` flag

```bash
docker build -f docker/monolithic/Dockerfile.nvidia -t digital-article:gpu .
docker run --gpus all -p 80:80 -v da-data:/app/data digital-article:gpu
```

## 🐧 Linux Note

On Linux without Docker Desktop, `host.docker.internal` may not resolve. Add:

```bash
docker run --add-host=host.docker.internal:host-gateway \
    -p 80:80 -v da-data:/app/data digital-article
```

## ⚠️ Build Context

All Docker commands must run from the **project root**:

```bash
# Correct
cd /path/to/digital-article
docker build -f docker/2-tiers/Dockerfile .

# Incorrect
cd /path/to/digital-article/docker
docker build -f 2-tiers/Dockerfile .
```

## 📚 More Documentation

- [2-Tiers README](./2-tiers/README.md) - Lightweight external LLM setup
- [Monolithic README](./monolithic/README.md) - Bundled Ollama setup
- [3-Tiers README](./3-tiers/README.md) - Microservices with docker-compose
