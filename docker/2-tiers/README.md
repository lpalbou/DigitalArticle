# Digital Article - 2-Tiers Docker

This is the **default** Docker configuration: Frontend + Backend in a single container, connecting to **external LLM providers** on the host machine.

## Quick Start

```bash
# From project root
docker build -t digital-article .
docker run -p 80:80 -v da-data:/app/data digital-article
```

The container connects to `http://host.docker.internal:1234/v1` by default (LMStudio's default port).

## Default Configuration

| Setting | Value |
|---------|-------|
| Provider | `openai-compatible` |
| Base URL | `http://host.docker.internal:1234/v1` |
| Model | *(auto-detect from server)* |

## Configuration Examples

### Custom URL/Port

```bash
# At runtime
docker run -p 80:80 -v da-data:/app/data \
    -e OPENAI_COMPATIBLE_BASE_URL=http://host.docker.internal:8080/v1 \
    digital-article

# At build time (baked into image)
docker build --build-arg OPENAI_COMPATIBLE_BASE_URL=http://myserver:8080/v1 \
    -t digital-article:custom .
```

### Specific Model

```bash
docker run -p 80:80 -v da-data:/app/data \
    -e LLM_MODEL=qwen2.5-coder-32b \
    digital-article
```

### Different Provider

```bash
# Ollama on host
docker run -p 80:80 -v da-data:/app/data \
    -e LLM_PROVIDER=ollama \
    -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
    -e LLM_MODEL=gemma3n:e2b \
    digital-article

# vLLM GPU server
docker run -p 80:80 -v da-data:/app/data \
    -e LLM_PROVIDER=vllm \
    -e VLLM_BASE_URL=http://gpu-server:8000/v1 \
    -e LLM_MODEL=Qwen/Qwen2.5-Coder-7B-Instruct \
    digital-article

# OpenAI cloud
docker run -p 80:80 -v da-data:/app/data \
    -e LLM_PROVIDER=openai \
    -e LLM_MODEL=gpt-4o \
    -e OPENAI_API_KEY=sk-... \
    digital-article

# Anthropic cloud
docker run -p 80:80 -v da-data:/app/data \
    -e LLM_PROVIDER=anthropic \
    -e LLM_MODEL=claude-3-5-sonnet-latest \
    -e ANTHROPIC_API_KEY=sk-ant-... \
    digital-article
```

## Environment Variables

### LLM Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `openai-compatible` | Provider to use |
| `LLM_MODEL` | *(empty)* | Model name (auto-detect if empty) |

### Provider URLs

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_COMPATIBLE_BASE_URL` | `http://host.docker.internal:1234/v1` | Generic OpenAI-compatible |
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | Ollama server |
| `LMSTUDIO_BASE_URL` | `http://host.docker.internal:1234/v1` | LMStudio server |
| `VLLM_BASE_URL` | `http://host.docker.internal:8000/v1` | vLLM server |

### API Keys (for cloud providers)

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `HUGGINGFACE_TOKEN` | HuggingFace token (optional) |
| `VLLM_API_KEY` | vLLM API key (optional) |
| `OPENAI_COMPATIBLE_API_KEY` | Generic API key (optional) |

## Build Arguments

Customize defaults at build time:

```bash
docker build \
    --build-arg LLM_PROVIDER=ollama \
    --build-arg LLM_MODEL=gemma3n:e2b \
    --build-arg OLLAMA_BASE_URL=http://host.docker.internal:11434 \
    -t digital-article:ollama .
```

| Argument | Default |
|----------|---------|
| `LLM_PROVIDER` | `openai-compatible` |
| `LLM_MODEL` | *(empty)* |
| `OPENAI_COMPATIBLE_BASE_URL` | `http://host.docker.internal:1234/v1` |
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` |
| `LMSTUDIO_BASE_URL` | `http://host.docker.internal:1234/v1` |
| `VLLM_BASE_URL` | `http://host.docker.internal:8000/v1` |

## Linux Note

On Linux without Docker Desktop, `host.docker.internal` may not resolve:

```bash
docker run --add-host=host.docker.internal:host-gateway \
    -p 80:80 -v da-data:/app/data digital-article
```

## Comparison with Monolithic

| Feature | 2-Tiers (this) | Monolithic |
|---------|----------------|------------|
| Image size | ~500MB | ~2GB |
| Build time | ~2 min | ~5 min |
| Ollama bundled | ❌ | ✅ |
| GPU on macOS | ✅ (host Ollama) | ❌ |
| Best for | Most users | Offline/self-contained |
