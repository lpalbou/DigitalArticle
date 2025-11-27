# Digital Article - Unified Monolithic Docker

This directory contains the **Monolithic** deployment option, where all services (Frontend, Backend, Ollama) run inside a **single Docker container**.

## Available Images

We provide 2 variants optimized for different hardware. All variants provide the same functionality but differ in base image and hardware acceleration support.

| Variant | File | Optimized For | GPU Support |
|---------|------|---------------|-------------|
| **Standard / CPU** | `Dockerfile` | Generic x86/ARM servers | No (CPU Inference) |
| **NVIDIA CUDA** | `Dockerfile.nvidia` | Linux with NVIDIA GPUs | **Yes (CUDA)** |

*Note: Docker on macOS cannot access the Metal GPU. For Apple Silicon Macs, use native Ollama on host and point the container to it via `OLLAMA_BASE_URL=http://host.docker.internal:11434`.*

## How to Build & Run

**IMPORTANT:** All build commands must be run from the **project root directory**, not from inside the `docker/` folder.

### Option A: Direct Build (Recommended)

1. Navigate to project root:
   ```bash
   cd /path/to/digital-article
   ```

2. Build the image for your hardware:

   **Standard/CPU:**
   ```bash
   docker build -f docker/monolithic/Dockerfile -t digital-article:unified .
   ```

   **NVIDIA GPU:**
   ```bash
   docker build -f docker/monolithic/Dockerfile.nvidia -t digital-article:unified .
   ```

3. Run the container:
   ```bash
   # Standard (uses bundled Ollama)
   docker run -p 80:80 -v ./data:/app/data digital-article:unified
   
   # NVIDIA GPU (requires --gpus all)
   docker run --gpus all -p 80:80 -v ./data:/app/data digital-article:unified
   ```

### Option B: Copy to Root (For PaaS/Platforms)

Some deployment platforms (like Railway, Render, or specific CI/CD pipelines) expect a `Dockerfile` at the root of the repository.

1. **Copy the appropriate file to the root:**

   ```bash
   # For Standard/Linux
   cp docker/monolithic/Dockerfile ./Dockerfile

   # For NVIDIA GPU Servers
   cp docker/monolithic/Dockerfile.nvidia ./Dockerfile
   ```

2. **Build normally:**
   ```bash
   docker build -t digital-article:unified .
   ```

## LLM Provider Configuration

The container supports multiple LLM providers via environment variables. This follows Docker conventions (env vars over config files).

### Default: Ollama (Local Inference)

```bash
docker run -p 80:80 \
    -v digital-article-data:/app/data \
    -v digital-article-models:/models \
    digital-article:unified
```

By default, the container:
- Starts the bundled Ollama server
- Pulls the configured model (default: `gemma3n:e2b`)
- Uses local CPU/GPU inference

### Using OpenAI

```bash
docker run -p 80:80 \
    -v digital-article-data:/app/data \
    -e LLM_PROVIDER=openai \
    -e LLM_MODEL=gpt-4o \
    -e OPENAI_API_KEY=sk-your-key-here \
    digital-article:unified
```

**Note:** When using external providers, Ollama is not started (saves resources).

### Using Anthropic

```bash
docker run -p 80:80 \
    -v digital-article-data:/app/data \
    -e LLM_PROVIDER=anthropic \
    -e LLM_MODEL=claude-3-5-sonnet-latest \
    -e ANTHROPIC_API_KEY=sk-ant-your-key-here \
    digital-article:unified
```

### Using LMStudio (External Server)

```bash
docker run -p 80:80 \
    -v digital-article-data:/app/data \
    -e LLM_PROVIDER=lmstudio \
    -e LLM_MODEL=qwen/qwen3-32b \
    digital-article:unified
```

**Note:** LMStudio must be running on your host machine. The backend will connect to `http://localhost:1234` by default.

### Using HuggingFace

```bash
docker run -p 80:80 \
    -v digital-article-data:/app/data \
    -e LLM_PROVIDER=huggingface \
    -e LLM_MODEL=Qwen/Qwen2.5-Coder-32B-Instruct \
    -e HUGGINGFACE_TOKEN=hf_your_token \
    digital-article:unified
```

### Using External Ollama (e.g., Native on Mac)

For better performance on Apple Silicon, run Ollama natively and point the container to it:

```bash
# On your Mac, start Ollama normally
ollama serve

# Run container pointing to host's Ollama
docker run -p 80:80 \
    -v digital-article-data:/app/data \
    -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
    digital-article:unified
```

## Environment Variables Reference

| Variable | Description | Default |
|----------|-------------|---------|
| **LLM Configuration** | | |
| `LLM_PROVIDER` | LLM provider (`ollama`, `openai`, `anthropic`, `lmstudio`, `huggingface`) | `ollama` |
| `LLM_MODEL` | Model name for the selected provider | `gemma3n:e2b` |
| `OPENAI_API_KEY` | API key for OpenAI | *(empty)* |
| `ANTHROPIC_API_KEY` | API key for Anthropic | *(empty)* |
| `HUGGINGFACE_TOKEN` | Token for HuggingFace (optional for public models) | *(empty)* |
| **Path Configuration** | | |
| `NOTEBOOKS_DIR` | Path to notebooks storage | `/app/data/notebooks` |
| `WORKSPACE_DIR` | Path to workspace storage | `/app/data/workspace` |
| `OLLAMA_MODELS` | Path to Ollama model storage | `/models` |
| `OLLAMA_BASE_URL` | Ollama API endpoint (for external Ollama) | `http://localhost:11434` |
| **Runtime** | | |
| `LOG_LEVEL` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `INFO` |

## Architecture

The monolithic container uses `supervisord` to manage multiple processes:
1. **Nginx (Port 80):** Serves frontend and proxies API requests.
2. **FastAPI Backend (Port 8000):** Core application logic (internal only).
3. **Ollama (Port 11434):** LLM inference engine (internal only, started only if `LLM_PROVIDER=ollama`).

Data is persisted in volumes:
- `/app/data`: Notebooks and workspace files.
- `/models`: Large LLM model files (cached, only used with Ollama).

## Configuration Priority

The application reads configuration in this priority order:

1. **Environment variables** (highest priority) - for Docker deployments
2. **config.json** - for local development
3. **Built-in defaults** (lowest priority)

This means you can always override any setting at runtime using `-e VAR=value`.
