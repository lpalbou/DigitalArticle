"""
Model Management API endpoints.

Provides model download/pull functionality using AbstractCore's unified download_model() API.
Uses Server-Sent Events (SSE) for streaming download progress.

Supported providers:
- ollama: Local Ollama server
- huggingface: HuggingFace Hub models
- mlx: MLX models (Apple Silicon only, not available in Docker)

Note: LMStudio does not have a REST API for downloading models.
      Users must download models via LMStudio GUI or `lms get` CLI on their host machine.
"""

import json
import logging
import os
import httpx
from typing import AsyncGenerator, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..services.user_settings_service import get_user_settings_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/models", tags=["models"])


class ModelPullRequest(BaseModel):
    """Request to pull/download a model."""
    provider: str  # 'ollama', 'huggingface', or 'mlx'
    model: str
    auth_token: Optional[str] = None  # Optional token for gated models


class ModelPullStatus(BaseModel):
    """Status of a model pull operation."""
    status: str  # 'starting', 'downloading', 'verifying', 'complete', 'error'
    progress: Optional[float] = None  # 0-100
    current_size: Optional[str] = None
    total_size: Optional[str] = None
    message: Optional[str] = None


def format_bytes(size: Optional[int]) -> Optional[str]:
    """Format bytes to human-readable string."""
    if size is None:
        return None
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


async def stream_model_download(
    provider: str, 
    model: str, 
    token: Optional[str] = None,
    base_url: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """
    Stream model download progress via SSE using AbstractCore's download_model().
    
    This unified function handles all supported providers (Ollama, HuggingFace, MLX).
    """
    try:
        # Import AbstractCore's download API
        try:
            from abstractcore import download_model, DownloadStatus
        except ImportError:
            yield f"data: {json.dumps({'status': 'error', 'message': 'AbstractCore not installed or version < 2.6.0'})}\n\n"
            return
        
        logger.info(f"Starting model download: {provider}/{model}")
        
        # Stream progress from AbstractCore
        async for progress in download_model(provider, model, token=token, base_url=base_url):
            # Map AbstractCore's DownloadProgress to our SSE format
            status_data = {
                'status': progress.status.value,  # 'starting', 'downloading', 'verifying', 'complete', 'error'
                'message': progress.message,
                'progress': progress.percent or 0,
                'current_size': format_bytes(progress.downloaded_bytes),
                'total_size': format_bytes(progress.total_bytes),
            }
            
            yield f"data: {json.dumps(status_data)}\n\n"
            
            # Stop streaming on completion or error
            if progress.status in (DownloadStatus.COMPLETE, DownloadStatus.ERROR):
                break
                
    except Exception as e:
        logger.error(f"Error in model download stream: {e}")
        yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"


# Supported providers for model download
DOWNLOAD_SUPPORTED_PROVIDERS = {'ollama', 'huggingface', 'mlx'}


@router.post("/pull")
async def pull_model(request: ModelPullRequest):
    """
    Start pulling/downloading a model.
    
    Returns an SSE stream with progress updates.
    
    Supported providers:
    - ollama: Uses Ollama's /api/pull endpoint (via AbstractCore)
    - huggingface: Uses huggingface_hub.snapshot_download (via AbstractCore)
    - mlx: Uses MLX model download (via AbstractCore, Apple Silicon only)
    
    Note: LMStudio does not have a REST API for model downloads.
          Users must use the LMStudio GUI or `lms get` CLI on their host machine.
    """
    if request.provider not in DOWNLOAD_SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Provider '{request.provider}' does not support model pulling. "
                   f"Supported: {', '.join(DOWNLOAD_SUPPORTED_PROVIDERS)}. "
                   "LMStudio requires manual download via GUI or 'lms get' CLI."
        )
    
    logger.info(f"Starting model pull: {request.provider}/{request.model}")
    
    # Get provider-specific configuration
    service = get_user_settings_service()
    settings = service.get_settings()
    
    # Determine base_url for local providers
    base_url = None
    if request.provider == "ollama":
        base_url = settings.llm.base_urls.get("ollama", "http://localhost:11434")
    
    # Get auth token from request or environment
    auth_token = request.auth_token
    if not auth_token and request.provider == "huggingface":
        auth_token = os.environ.get('HUGGINGFACE_TOKEN')
    
    return StreamingResponse(
        stream_model_download(request.provider, request.model, token=auth_token, base_url=base_url),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@router.get("/available/{provider}")
async def get_available_models(provider: str):
    """
    Get list of available/cached models for a provider.
    
    For Ollama: queries local models from Ollama API
    For LMStudio: queries loaded models from LMStudio server
    For HuggingFace: lists locally cached models (not remote search)
    For MLX: lists locally cached MLX models
    For cloud providers: returns empty (models are predefined)
    """
    service = get_user_settings_service()
    settings = service.get_settings()
    
    if provider == "ollama":
        base_url = settings.llm.base_urls.get("ollama", "http://localhost:11434")
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    models = [m["name"] for m in data.get("models", [])]
                    return {"provider": provider, "models": models}
        except Exception as e:
            logger.warning(f"Failed to get Ollama models: {e}")
            return {"provider": provider, "models": [], "error": str(e)}
    
    elif provider == "lmstudio":
        base_url = settings.llm.base_urls.get("lmstudio", "http://localhost:1234/v1")
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{base_url}/models")
                if response.status_code == 200:
                    data = response.json()
                    models = [m["id"] for m in data.get("data", [])]
                    return {"provider": provider, "models": models}
        except Exception as e:
            logger.warning(f"Failed to get LMStudio models: {e}")
            return {"provider": provider, "models": [], "error": str(e)}
    
    elif provider == "huggingface":
        # List locally cached HuggingFace models
        try:
            from huggingface_hub import scan_cache_dir
            cache_info = scan_cache_dir()  # Respects HF_HOME automatically
            models = [repo.repo_id for repo in cache_info.repos]
            return {"provider": provider, "models": models}
        except ImportError:
            return {"provider": provider, "models": [], "error": "huggingface_hub not installed"}
        except Exception as e:
            logger.warning(f"Failed to scan HuggingFace cache: {e}")
            return {"provider": provider, "models": [], "error": str(e)}
    
    elif provider == "mlx":
        # List locally cached MLX models (same cache as HuggingFace)
        try:
            from huggingface_hub import scan_cache_dir
            cache_info = scan_cache_dir()
            # Filter for MLX models (typically have 'mlx' in name)
            models = [repo.repo_id for repo in cache_info.repos if 'mlx' in repo.repo_id.lower()]
            return {"provider": provider, "models": models}
        except ImportError:
            return {"provider": provider, "models": [], "error": "huggingface_hub not installed"}
        except Exception as e:
            logger.warning(f"Failed to scan MLX cache: {e}")
            return {"provider": provider, "models": [], "error": str(e)}
    
    else:
        return {"provider": provider, "models": [], "note": "Cloud providers have predefined models"}


@router.delete("/{provider}/{model:path}")
async def delete_model(provider: str, model: str):
    """
    Delete a model from a local provider.
    
    Only supported for Ollama (HuggingFace/MLX use shared cache).
    """
    if provider != "ollama":
        raise HTTPException(
            status_code=400,
            detail="Model deletion only supported for Ollama. "
                   "HuggingFace/MLX models share a cache - use `huggingface-cli delete-cache` to manage."
        )
    
    service = get_user_settings_service()
    settings = service.get_settings()
    base_url = settings.llm.base_urls.get("ollama", "http://localhost:11434")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                "DELETE",
                f"{base_url}/api/delete",
                json={"name": model}
            )
            if response.status_code == 200:
                return {"status": "success", "message": f"Model {model} deleted"}
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail=f"Cannot connect to Ollama at {base_url}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
