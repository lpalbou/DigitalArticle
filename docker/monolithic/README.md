# Digital Article - Unified Monolithic Docker

This directory contains the **Monolithic** deployment option, where all services (Frontend, Backend, Ollama) run inside a **single Docker container**.

## Available Images

We provide 3 variants optimized for different hardware. All variants provide the same functionality but differ in base image and hardware acceleration support.

| Variant | File | optimized For | GPU Support |
|---------|------|---------------|-------------|
| **Standard / CPU** | `Dockerfile` (or `Dockerfile.cpu`) | Generic x86/ARM servers | No (CPU Inference) |
| **Apple Silicon** | `Dockerfile.apple` | Mac M1/M2/M3 (ARM64) | No (CPU Inference)* |
| **NVIDIA CUDA** | `Dockerfile.nvidia` | Linux with NVIDIA GPUs | **Yes (CUDA)** |

*\*Note: Docker on macOS cannot access the Metal GPU. The Apple Silicon image is optimized for ARM64 CPU execution.*

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

   **Apple Silicon:**
   ```bash
   docker build -f docker/monolithic/Dockerfile.apple -t digital-article:unified .
   ```

   **NVIDIA GPU:**
   ```bash
   docker build -f docker/monolithic/Dockerfile.nvidia -t digital-article:unified .
   ```

3. Run the container:
   ```bash
   # Standard / Apple
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

   # For Apple Silicon Dev
   cp docker/monolithic/Dockerfile.apple ./Dockerfile

   # For NVIDIA GPU Servers
   cp docker/monolithic/Dockerfile.nvidia ./Dockerfile
   ```

2. **Build normally:**
   ```bash
   docker build -t digital-article:unified .
   ```

## Architecture

The monolithic container uses `supervisord` to manage multiple processes:
1. **Nginx (Port 80):** Serves frontend and proxies API requests.
2. **FastAPI Backend (Port 8000):** Core application logic (internal only).
3. **Ollama (Port 11434):** LLM inference engine (internal only).

Data is persisted in volumes:
- `/app/data`: Notebooks and workspace files.
- `/models`: Large LLM model files (cached).

## Configuration

The container auto-configures itself on first run.
- **First Run:** Takes 5-10 minutes to download the LLM model (qwen3-coder:30b).
- **Subsequent Runs:** Starts in seconds.
