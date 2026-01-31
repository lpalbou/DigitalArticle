# Backlog Item (Historical; migrated from legacy devnotes)

## Title
Response to Digital Article Feature Request: Model Download API

## Backlog ID
0014

## Priority
- **P2 (historical)**: migrated record from the legacy `docs/devnotes/` folder to keep governance artifacts in one system.

## Date / Time
Unknown (historical; migrated 2026-01-31)

## Short Summary
This file preserves a historical devnote that previously lived under `docs/backlog/completed/0014_abstractcore_model_download_api.md`. It has been migrated to `docs/backlog/completed/` so that historical investigations and fixes live under the same backlog governance system.

## Key Goals
- Preserve historical context without losing information.
- Keep the repository’s documentation graph navigable (no legacy devnotes folder).
- Enable future follow-up backlog items to reference this historical record.

## Scope

### To do
- Preserve the original devnote content under **Full Report** (verbatim aside from link-path adjustments due to relocation).
- Update references elsewhere in the docs to point to this new location.

### NOT to do
- Do not claim this migration implies the underlying runtime change is still current; treat as historical evidence.

## Dependencies

### Backlog dependencies (ordering)
- **None**

### ADR dependencies (must comply)
- **All ADRs are mandatory**: [`docs/adr/README.md`](../../adr/README.md)

### Points of vigilance (during execution)
- Keep the historical record intact.
- Ensure any updated links remain valid (run `python tools/validate_markdown_links.py`).

## References (source of truth)
- Legacy source: `docs/backlog/completed/0014_abstractcore_model_download_api.md` (removed after migration)
- Backlog/ADR governance: [`docs/backlog/README.md`](../README.md), [`docs/adr/README.md`](../../adr/README.md)

## Full Report (legacy devnote content)

# Response to Digital Article Feature Request: Model Download API

> **Devnote (historical):** This document records an upstream AbstractCore feature request/response. For current model download behavior in this repo, see `backend/app/api/models.py` and `docs/troubleshooting.md`.

## Implementation Complete ✅

Your feature request for a model download API has been implemented and will be available in **AbstractCore v2.6.0** (publishing today).

---

## What We Built

A provider-agnostic async model download API with real-time progress reporting, exactly as you requested. This eliminates the need for provider-specific logic in Digital Article.

### Key Features

- **Single unified API** for Ollama, HuggingFace, and MLX models
- **Async progress streaming** via Python async generators
- **Top-level import**: `from abstractcore import download_model`
- **Real-time progress**: Status, message, percent, bytes downloaded
- **Error handling**: Clear messages for all failure modes
- **Zero breaking changes**: Fully backward compatible

---

## How to Use It in Digital Article

### 1. Update AbstractCore

```bash
pip install --upgrade abstractcore
# Or in your requirements.txt:
# abstractcore>=2.6.0
```

### 2. Replace Your Current Implementation

**Before** (your current code):
```python
from huggingface_hub import snapshot_download, HfFileSystem
from huggingface_hub.utils import GatedRepoError, RepositoryNotFoundError

# Provider-specific knowledge you had to maintain
async def download_huggingface_model(model: str, token: str = None):
    fs = HfFileSystem(token=token)
    files = fs.ls(model, detail=True)  # Check if exists
    snapshot_download(repo_id=model, token=token)  # Download

# For Ollama, completely different API
async with client.stream("POST", f"{base_url}/api/pull", json={"name": model}):
    # Parse NDJSON progress...
```

**After** (with AbstractCore v2.6.0):
```python
from abstractcore import download_model

# Single API for all providers
async for progress in download_model(provider, model, token=token):
    # Unified progress format for all providers
    yield f"data: {json.dumps({
        'status': progress.status.value,
        'message': progress.message,
        'percent': progress.percent,
        'downloaded': progress.downloaded_bytes,
        'total': progress.total_bytes
    })}\n\n"
```

### 3. Complete Digital Article Integration

Here's how to integrate into your Docker deployment web UI:

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from abstractcore import download_model, DownloadStatus
import json

app = FastAPI()

@app.get("/api/models/download")
async def download_model_endpoint(
    provider: str,  # "ollama", "huggingface", or "mlx"
    model: str,
    token: str = None
):
    """Stream model download progress to frontend via SSE."""

    async def progress_stream():
        try:
            async for progress in download_model(provider, model, token=token):
                # Send progress updates
                yield f"data: {json.dumps({
                    'status': progress.status.value,
                    'message': progress.message,
                    'percent': progress.percent,
                    'downloaded_bytes': progress.downloaded_bytes,
                    'total_bytes': progress.total_bytes
                })}\n\n"

                # Check for completion or error
                if progress.status == DownloadStatus.COMPLETE:
                    yield f"data: {json.dumps({'done': True})}\n\n"
                    break
                elif progress.status == DownloadStatus.ERROR:
                    yield f"data: {json.dumps({'error': progress.message})}\n\n"
                    break

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        progress_stream(),
        media_type="text/event-stream"
    )
```

### 4. Frontend Integration (React Example)

```typescript
// Your Digital Article frontend
const downloadModel = async (provider: string, model: string, token?: string) => {
  const url = `/api/models/download?provider=${provider}&model=${model}${token ? `&token=${token}` : ''}`;
  const eventSource = new EventSource(url);

  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);

    // Update your UI with progress
    setDownloadProgress({
      status: data.status,
      message: data.message,
      percent: data.percent
    });

    if (data.done) {
      eventSource.close();
      showSuccess('Model downloaded successfully!');
    }

    if (data.error) {
      eventSource.close();
      showError(data.error);
    }
  };
};
```

---

## Provider-Specific Examples

### Ollama Models (with full progress)

```python
from abstractcore import download_model

async for progress in download_model("ollama", "llama3:8b"):
    print(f"{progress.status.value}: {progress.message}")
    if progress.percent:
        print(f"  Progress: {progress.percent:.1f}%")
        print(f"  Downloaded: {progress.downloaded_bytes} / {progress.total_bytes} bytes")
```

**Output:**
```
starting: Pulling llama3:8b from Ollama...
downloading: pulling manifest
downloading: downloading digestname
  Progress: 45.2%
  Downloaded: 523456789 / 1157890123 bytes
downloading: verifying sha256 digest
complete: Successfully pulled llama3:8b
  Progress: 100.0%
```

### HuggingFace Models

```python
# Public model
async for progress in download_model("huggingface", "meta-llama/Llama-2-7b"):
    print(progress.message)

# Gated model with token
async for progress in download_model(
    "huggingface",
    "meta-llama/Llama-2-7b",
    token="hf_..."
):
    print(progress.message)
```

### MLX Models (Apple Silicon)

```python
async for progress in download_model("mlx", "mlx-community/Qwen3-4B-4bit"):
    print(progress.message)
```

### Custom Ollama Server

```python
# For non-default Ollama installations
async for progress in download_model(
    "ollama",
    "gemma3:1b",
    base_url="http://custom-server:11434"
):
    print(progress.message)
```

---

## Progress Information Structure

```python
from abstractcore import DownloadProgress, DownloadStatus

# DownloadProgress dataclass fields:
progress.status          # DownloadStatus enum
progress.message         # Human-readable status message
progress.percent         # Optional: 0-100 progress percentage
progress.downloaded_bytes  # Optional: bytes downloaded
progress.total_bytes     # Optional: total size

# DownloadStatus enum values:
DownloadStatus.STARTING    # Download initiated
DownloadStatus.DOWNLOADING # In progress
DownloadStatus.VERIFYING   # Verifying integrity
DownloadStatus.COMPLETE    # Successfully completed
DownloadStatus.ERROR       # Failed with error
```

---

## Error Handling

All errors are returned as progress updates with `DownloadStatus.ERROR`:

```python
async for progress in download_model("huggingface", "nonexistent/model"):
    if progress.status == DownloadStatus.ERROR:
        print(f"Download failed: {progress.message}")
        # Example messages:
        # - "Model 'nonexistent/model' not found on HuggingFace Hub"
        # - "Model requires authentication. Provide token parameter."
        # - "Cannot connect to Ollama server at http://localhost:11434"
```

---

## Provider Support Matrix

| Provider | Support | Progress Detail | Method |
|----------|---------|-----------------|--------|
| **Ollama** | ✅ Full | Percent + bytes | `/api/pull` streaming NDJSON |
| **HuggingFace** | ✅ Full | Start/complete | `huggingface_hub.snapshot_download` |
| **MLX** | ✅ Full | Start/complete | Same as HuggingFace |
| LMStudio | ❌ Not supported | N/A | No download API (CLI/GUI only) |
| OpenAI | ❌ Not supported | N/A | Cloud-only |
| Anthropic | ❌ Not supported | N/A | Cloud-only |

---

## Benefits for Digital Article

1. **Eliminates Duplicate Code**: No more maintaining provider-specific download logic
2. **Unified Interface**: Same API regardless of provider
3. **Better UX**: Rich progress information for your users
4. **Error Handling**: Clear, actionable error messages
5. **Future-Proof**: New providers automatically supported
6. **Production-Ready**: Tested with real implementations, 11/11 tests passing
7. **Async-Native**: Natural integration with FastAPI and async frameworks

---

## Testing

All functionality tested with real implementations (no mocking):

```bash
# Install AbstractCore 2.6.0
pip install abstractcore>=2.6.0

# Test Ollama download
python -c "
import asyncio
from abstractcore import download_model

async def test():
    async for p in download_model('ollama', 'gemma3:1b'):
        print(f'{p.status.value}: {p.message}')

asyncio.run(test())
"

# Test HuggingFace download
python -c "
import asyncio
from abstractcore import download_model

async def test():
    async for p in download_model('huggingface', 'hf-internal-testing/tiny-random-gpt2'):
        print(p.message)

asyncio.run(test())
"
```

---

## Additional Features in v2.6.0

While implementing your feature, we also added:

### Custom Base URLs (Bonus)

Configure OpenAI-compatible proxies for observability and cost tracking:

```python
from abstractcore import create_llm

# Use Portkey or similar proxy
llm = create_llm(
    "openai",
    model="gpt-4o-mini",
    base_url="https://api.portkey.ai/v1",
    api_key="your-portkey-key"
)
```

---

## Documentation

Complete documentation available in AbstractCore v2.6.0:

- **Quick Reference**: See `llms.txt` for AI-friendly documentation
- **Full Guide**: See `llms-full.txt` for comprehensive examples
- **Implementation (current repo)**: see [`backend/app/api/models.py`](../../../backend/app/api/models.py) and [`docs/troubleshooting.md`](../../troubleshooting.md)

---

## Questions or Issues?

If you encounter any issues integrating this into Digital Article, please:

1. Check the implementation in [`backend/app/api/models.py`](../../../backend/app/api/models.py) for detailed examples
2. Review the test suite: `tests/download/test_model_download.py`
3. Open an issue on GitHub with your specific use case

---

## Summary

✅ **Feature Complete**: Exactly what you requested
✅ **Production-Ready**: 11/11 tests passing with real implementations
✅ **Zero Breaking Changes**: Fully backward compatible
✅ **Available Now**: AbstractCore v2.6.0

Thank you for the feature request! This capability will benefit all AbstractCore users deploying in containerized environments.

---

*AbstractCore Team*
*December 1, 2025*

