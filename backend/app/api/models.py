"""
Model Management API endpoints.

Provides model download/pull functionality for Ollama and HuggingFace.
Uses Server-Sent Events (SSE) for streaming download progress.

Note: LMStudio does not have a REST API for downloading models.
      Users must download models via LMStudio GUI or `lms get` CLI on their host machine.
"""

import asyncio
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
    provider: str  # 'ollama' or 'huggingface'
    model: str
    auth_token: Optional[str] = None  # Optional HuggingFace token for gated models


class ModelPullStatus(BaseModel):
    """Status of a model pull operation."""
    status: str  # 'downloading', 'complete', 'error'
    progress: Optional[float] = None  # 0-100
    current_size: Optional[str] = None
    total_size: Optional[str] = None
    message: Optional[str] = None


def format_bytes(size: int) -> str:
    """Format bytes to human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


async def stream_ollama_pull(base_url: str, model: str) -> AsyncGenerator[str, None]:
    """
    Stream Ollama model pull progress via SSE.
    
    Ollama's /api/pull endpoint returns NDJSON with progress updates.
    """
    try:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                f"{base_url}/api/pull",
                json={"name": model, "stream": True},
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    yield f"data: {json.dumps({'status': 'error', 'message': error_text.decode()})}\n\n"
                    return

                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    
                    try:
                        data = json.loads(line)
                        
                        # Parse Ollama progress format
                        status_data: dict = {"status": "downloading"}
                        
                        if "status" in data:
                            status_msg = data["status"]
                            
                            if "pulling" in status_msg:
                                status_data["message"] = status_msg
                            elif status_msg == "success":
                                status_data = {
                                    "status": "complete",
                                    "message": f"Model {model} downloaded successfully"
                                }
                            else:
                                status_data["message"] = status_msg
                        
                        # Progress info
                        if "completed" in data and "total" in data:
                            completed = data["completed"]
                            total = data["total"]
                            if total > 0:
                                status_data["progress"] = round((completed / total) * 100, 1)
                                status_data["current_size"] = format_bytes(completed)
                                status_data["total_size"] = format_bytes(total)
                        
                        yield f"data: {json.dumps(status_data)}\n\n"
                        
                    except json.JSONDecodeError:
                        continue

        # Final success message
        yield f"data: {json.dumps({'status': 'complete', 'message': f'Model {model} is ready'})}\n\n"
        
    except httpx.ConnectError:
        yield f"data: {json.dumps({'status': 'error', 'message': f'Cannot connect to Ollama at {base_url}'})}\n\n"
    except Exception as e:
        logger.error(f"Error pulling model: {e}")
        yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"


async def stream_huggingface_download(model: str, auth_token: Optional[str] = None) -> AsyncGenerator[str, None]:
    """
    Stream HuggingFace model download progress via SSE.
    
    Uses huggingface_hub.snapshot_download which downloads model files to HF_HOME cache.
    Progress is reported via callbacks.
    """
    try:
        # Import here to avoid startup issues if HF not installed
        try:
            from huggingface_hub import snapshot_download, HfFileSystem
            from huggingface_hub.utils import GatedRepoError, RepositoryNotFoundError
        except ImportError:
            yield f"data: {json.dumps({'status': 'error', 'message': 'huggingface_hub not installed. Install with: pip install huggingface_hub'})}\n\n"
            return
        
        # HF_HOME environment variable is respected by huggingface_hub automatically
        # No need to pass cache_dir - the library will use $HF_HOME/hub/
        
        yield f"data: {json.dumps({'status': 'downloading', 'message': f'Starting download of {model}...'})}\n\n"
        
        # Check if model exists first
        try:
            fs = HfFileSystem(token=auth_token)
            files = fs.ls(model, detail=True)
            total_size = sum(f.get('size', 0) for f in files if f.get('type') == 'file')
            yield f"data: {json.dumps({'status': 'downloading', 'message': f'Found {len(files)} files, total size: {format_bytes(total_size)}'})}\n\n"
        except RepositoryNotFoundError:
            yield f"data: {json.dumps({'status': 'error', 'message': f'Model {model} not found on HuggingFace'})}\n\n"
            return
        except GatedRepoError:
            yield f"data: {json.dumps({'status': 'error', 'message': f'Model {model} is gated. Please provide an auth token with access.'})}\n\n"
            return
        except Exception as e:
            yield f"data: {json.dumps({'status': 'downloading', 'message': f'Checking model... (some info unavailable: {e})'})}\n\n"
        
        # Perform download in a thread to not block
        import concurrent.futures
        
        def do_download():
            return snapshot_download(
                repo_id=model,
                token=auth_token,
                resume_download=True,
            )
        
        yield f"data: {json.dumps({'status': 'downloading', 'message': 'Downloading model files... This may take a while.'})}\n\n"
        
        # Run download in executor
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            try:
                local_path = await loop.run_in_executor(executor, do_download)
                yield f"data: {json.dumps({'status': 'complete', 'message': f'Model {model} downloaded to {local_path}', 'progress': 100})}\n\n"
            except GatedRepoError:
                yield f"data: {json.dumps({'status': 'error', 'message': f'Model {model} requires authentication. Please provide a valid HuggingFace token.'})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'status': 'error', 'message': f'Download failed: {str(e)}'})}\n\n"
                
    except Exception as e:
        logger.error(f"Error downloading HuggingFace model: {e}")
        yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"


@router.post("/pull")
async def pull_model(request: ModelPullRequest):
    """
    Start pulling/downloading a model.
    
    Returns an SSE stream with progress updates.
    
    Supported providers:
    - ollama: Uses Ollama's /api/pull endpoint
    - huggingface: Uses huggingface_hub.snapshot_download
    
    Note: LMStudio does not have a REST API for model downloads.
          Users must use the LMStudio GUI or `lms get` CLI on their host machine.
    """
    if request.provider not in ["ollama", "huggingface"]:
        raise HTTPException(
            status_code=400,
            detail=f"Provider '{request.provider}' does not support model pulling. "
                   "LMStudio requires manual download via GUI or 'lms get' CLI."
        )
    
    logger.info(f"Starting model pull: {request.provider}/{request.model}")
    
    if request.provider == "ollama":
        # Get base URL from user settings
        service = get_user_settings_service()
        settings = service.get_settings()
        base_url = settings.llm.base_urls.get("ollama", "http://localhost:11434")
        
        return StreamingResponse(
            stream_ollama_pull(base_url, request.model),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            }
        )
    
    elif request.provider == "huggingface":
        # Use auth token from request or fall back to environment
        auth_token = request.auth_token or os.environ.get('HUGGINGFACE_TOKEN')
        
        return StreamingResponse(
            stream_huggingface_download(request.model, auth_token),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )


@router.get("/available/{provider}")
async def get_available_models(provider: str):
    """
    Get list of available models for a provider.
    
    For Ollama: queries local models from Ollama API
    For LMStudio: queries loaded models from LMStudio server
    For HuggingFace: lists locally cached models (not remote search)
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
        # scan_cache_dir() respects HF_HOME automatically when no arg is passed
        try:
            from huggingface_hub import scan_cache_dir
            
            cache_info = scan_cache_dir()  # Uses $HF_HOME/hub automatically
            
            models = [repo.repo_id for repo in cache_info.repos]
            return {"provider": provider, "models": models}
        except ImportError:
            return {"provider": provider, "models": [], "error": "huggingface_hub not installed"}
        except Exception as e:
            logger.warning(f"Failed to scan HuggingFace cache: {e}")
            return {"provider": provider, "models": [], "error": str(e)}
    
    else:
        return {"provider": provider, "models": [], "note": "Cloud providers have predefined models"}


@router.delete("/{provider}/{model}")
async def delete_model(provider: str, model: str):
    """
    Delete a model from a local provider.
    
    Only supported for Ollama.
    """
    if provider != "ollama":
        raise HTTPException(
            status_code=400,
            detail="Model deletion only supported for Ollama"
        )
    
    service = get_user_settings_service()
    settings = service.get_settings()
    base_url = settings.llm.base_urls.get("ollama", "http://localhost:11434")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(
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

