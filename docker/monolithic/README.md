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
   docker run -p 80:80 -v ./data:/app/data \
     -e DA_CONTACT_EMAIL=support@example.com \
     digital-article:unified
   
   # NVIDIA GPU (requires --gpus all)
   docker run --gpus all -p 80:80 -v ./data:/app/data \
     -e DA_CONTACT_EMAIL=support@example.com \
     digital-article:unified
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

### Supported Providers

| Provider | Type | Support | Notes |
|----------|------|---------|-------|
| **Ollama** | Local (bundled) | ✅ Full | Binary bundled in image, default |
| **OpenAI** | Cloud API | ✅ Full | Requires `OPENAI_API_KEY` |
| **Anthropic** | Cloud API | ✅ Full | Requires `ANTHROPIC_API_KEY` |
| **LMStudio** | External server | ✅ Full | Desktop app on host, container connects to it |
| **HuggingFace** | Local inference | ✅ Full | Includes torch, transformers |
| **vLLM** | External GPU server | ✅ Full | High-throughput inference, NVIDIA CUDA only |
| **OpenAI-Compatible** | External server | ✅ Full | Any OpenAI-compatible API (llama.cpp, LocalAI, etc.) |

### Default: Ollama (Local Inference)

```bash
docker run -p 80:80 \
    -v digital-article-data:/app/data \
    -v digital-article-models:/models \
    digital-article:unified
```

> **Volume Note:** The `/models` directory contains subdirectories for each provider (`/models/ollama`, `/models/huggingface`). Using a single volume for both ensures persistent model caching.

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

LMStudio is a **desktop GUI application** that cannot run inside Docker. You must run it on your host machine and point the container to it.

```bash
# 1. On your host: Start LMStudio and load a model

# 2. Run container pointing to host's LMStudio
docker run -p 80:80 \
    -v digital-article-data:/app/data \
    -e LLM_PROVIDER=lmstudio \
    -e LLM_MODEL=qwen/qwen3-32b \
    -e LMSTUDIO_BASE_URL=http://host.docker.internal:1234/v1 \
    digital-article:unified
```

**Note:** Use `LMSTUDIO_BASE_URL` to specify the LMStudio server address. On Docker Desktop, use `http://host.docker.internal:1234/v1`. For Linux, you may need `--network host` or an explicit IP.

### Using HuggingFace

```bash
docker run -p 80:80 \
    -v digital-article-data:/app/data \
    -v digital-article-models:/models \
    -e LLM_PROVIDER=huggingface \
    -e LLM_MODEL=Qwen/Qwen2.5-Coder-32B-Instruct \
    -e HUGGINGFACE_TOKEN=hf_your_token \
    digital-article:unified
```

**Note:** HuggingFace runs models locally inside the container. Models are cached in `/models/huggingface` (set via `HF_HOME`). Ensure sufficient RAM/VRAM for your chosen model. Models can be downloaded via the Settings UI or will be auto-downloaded on first use.

### Using vLLM (High-Throughput GPU Inference)

vLLM is a high-performance inference engine for NVIDIA CUDA GPUs. Run it on a separate GPU server and point the container to it:

```bash
# 1. On your GPU server: Start vLLM
# python -m vllm.entrypoints.openai.api_server --model Qwen/Qwen2.5-Coder-7B-Instruct --port 8000

# 2. Run container pointing to GPU server's vLLM
docker run -p 80:80 \
    -v digital-article-data:/app/data \
    -e LLM_PROVIDER=vllm \
    -e LLM_MODEL=Qwen/Qwen2.5-Coder-7B-Instruct \
    -e VLLM_BASE_URL=http://your-gpu-server:8000/v1 \
    digital-article:unified
```

**Note:** vLLM requires NVIDIA CUDA hardware. Use `VLLM_BASE_URL` to specify the server address.

### Using OpenAI-Compatible (Generic Provider)

Works with any server implementing the OpenAI API format: llama.cpp, text-generation-webui, LocalAI, FastChat, Aphrodite, SGLang, or custom proxies.

```bash
# Example with llama.cpp server running on host
docker run -p 80:80 \
    -v digital-article-data:/app/data \
    -e LLM_PROVIDER=openai-compatible \
    -e LLM_MODEL=my-local-model \
    -e OPENAI_COMPATIBLE_BASE_URL=http://host.docker.internal:8080/v1 \
    digital-article:unified
```

**Note:** Use `OPENAI_COMPATIBLE_BASE_URL` to specify the server address. Most local servers don't require an API key, but if needed, set `OPENAI_COMPATIBLE_API_KEY`.

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
| `LLM_PROVIDER` | LLM provider (`ollama`, `openai`, `anthropic`, `lmstudio`, `huggingface`, `vllm`, `openai-compatible`) | `ollama` |
| `LLM_MODEL` | Model name for the selected provider | `gemma3n:e2b` |
| `OPENAI_API_KEY` | API key for OpenAI | *(empty)* |
| `ANTHROPIC_API_KEY` | API key for Anthropic | *(empty)* |
| `HUGGINGFACE_TOKEN` | Token for HuggingFace (optional for public models) | *(empty)* |
| `VLLM_API_KEY` | API key for vLLM (optional, most servers don't require it) | *(empty)* |
| `OPENAI_COMPATIBLE_API_KEY` | API key for OpenAI-compatible servers (optional) | *(empty)* |
| **Path Configuration** | | |
| `NOTEBOOKS_DIR` | Path to notebooks storage | `/app/data/notebooks` |
| `WORKSPACE_DIR` | Path to workspace storage | `/app/data/workspace` |
| `OLLAMA_MODELS` | Path to Ollama model storage | `/models/ollama` |
| `HF_HOME` | Path to HuggingFace model cache | `/models/huggingface` |
| `OLLAMA_BASE_URL` | Ollama API endpoint (for external Ollama) | `http://localhost:11434` |
| `LMSTUDIO_BASE_URL` | LMStudio API endpoint (for external LMStudio) | `http://localhost:1234/v1` |
| `VLLM_BASE_URL` | vLLM API endpoint (for external vLLM server) | `http://localhost:8000/v1` |
| `OPENAI_COMPATIBLE_BASE_URL` | Generic OpenAI-compatible API endpoint | `http://localhost:8080/v1` |
| **Runtime** | | |
| `LOG_LEVEL` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `INFO` |

## Architecture

The monolithic container uses `supervisord` to manage multiple processes:
1. **Nginx (Port 80):** Serves frontend and proxies API requests.
2. **FastAPI Backend (Port 8000):** Core application logic (internal only).
3. **Ollama (Port 11434):** LLM inference engine (internal only, started only if `LLM_PROVIDER=ollama`).

Data is persisted in volumes:
- `/app/data`: Notebooks and workspace files.
- `/models/ollama`: Ollama model files (cached).
- `/models/huggingface`: HuggingFace model cache (via `HF_HOME`).

## Configuration Priority

The application reads configuration in this priority order:

1. **Environment variables** (highest priority) - for Docker deployments
2. **config.json** - for local development
3. **Built-in defaults** (lowest priority)

This means you can always override any setting at runtime using `-e VAR=value`.
