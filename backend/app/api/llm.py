"""
API endpoints for LLM operations.

This module provides REST endpoints for LLM-related functionality
such as code generation, explanation, and provider management.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor

from ..services.shared import notebook_service
from ..config import config, CONFIG_FILE
from abstractcore.providers import get_all_providers_with_models
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Get LLM service from shared notebook service
llm_service = notebook_service.llm_service


class CodeGenerationRequest(BaseModel):
    """Request model for code generation."""
    prompt: str
    context: dict = {}


class CodeExplanationRequest(BaseModel):
    """Request model for code explanation."""
    code: str


class CodeImprovementRequest(BaseModel):
    """Request model for code improvement."""
    prompt: str
    code: str
    error_message: str = None


@router.post("/generate-code")
async def generate_code(request: CodeGenerationRequest):
    """Generate Python code from a natural language prompt."""
    try:
        code = llm_service.generate_code_from_prompt(
            request.prompt,
            request.context if request.context else None
        )
        return {"code": code}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate code: {str(e)}"
        )


@router.post("/explain-code")
async def explain_code(request: CodeExplanationRequest):
    """Generate a natural language explanation of Python code."""
    try:
        explanation = llm_service.explain_code(request.code)
        return {"explanation": explanation}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to explain code: {str(e)}"
        )


@router.post("/improve-code")
async def improve_code(request: CodeImprovementRequest):
    """Suggest improvements or fixes for Python code."""
    try:
        improved_code = llm_service.suggest_improvements(
            request.prompt,
            request.code,
            request.error_message
        )
        return {"improved_code": improved_code}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to improve code: {str(e)}"
        )


class ProviderInfo(BaseModel):
    """Information about an LLM provider."""
    name: str
    display_name: str
    available: bool
    default_model: str
    models: List[str]


class ProviderSelectionRequest(BaseModel):
    """Request to set provider and model."""
    provider: str
    model: str
    notebook_id: Optional[str] = None  # If provided, also update this specific notebook


@router.get("/providers", response_model=List[ProviderInfo])
async def get_available_providers():
    """
    Get list of available LLM providers (without models for speed).
    Use /providers/{provider}/models to get models for a specific provider.

    ALWAYS queries AbstractCore fresh - no caching.
    Sets API keys and base URLs using AbstractCore v2.6.2 programmatic configuration.
    """
    logger.info("🔍 Detecting available LLM providers...")

    # Get saved settings
    from ..services.user_settings_service import get_user_settings_service
    from abstractcore.config import configure_provider
    import os

    settings_service = get_user_settings_service()
    settings = settings_service.get_settings()

    # Set API keys in environment if they exist (for cloud providers)
    if settings.llm.api_keys.get('openai'):
        os.environ['OPENAI_API_KEY'] = settings.llm.api_keys['openai']
    if settings.llm.api_keys.get('anthropic'):
        os.environ['ANTHROPIC_API_KEY'] = settings.llm.api_keys['anthropic']
    if settings.llm.api_keys.get('huggingface'):
        os.environ['HUGGINGFACE_TOKEN'] = settings.llm.api_keys['huggingface']

    # Configure base URLs programmatically (AbstractCore v2.6.5)
    # This makes all subsequent create_llm() calls use these URLs automatically
    # Supports: ollama, lmstudio, vllm, openai-compatible, openai, anthropic
    for provider, base_url in settings.llm.base_urls.items():
        if base_url and base_url.strip():  # Only configure if URL is set
            configure_provider(provider, base_url=base_url)
            logger.debug(f"📍 Configured {provider} base_url: {base_url}")

    # Use AbstractCore's provider registry - get metadata only (no models)
    # This will now see the API keys and configured base URLs
    loop = asyncio.get_event_loop()

    def _get_providers():
        return get_all_providers_with_models(include_models=False)

    # Run in thread pool to avoid blocking
    providers = await loop.run_in_executor(None, _get_providers)

    # Convert to our ProviderInfo format (only include available providers)
    results = [
        ProviderInfo(
            name=p['name'],
            display_name=p['display_name'],
            available=True,
            default_model='',
            models=[]  # Models fetched separately via /providers/{provider}/models
        )
        for p in providers
        if p.get('status') == 'available'
    ]

    if results:
        logger.info(f"🏁 Found {len(results)} available providers")
    else:
        logger.warning("⚠️ No LLM providers found")

    return results


@router.get("/providers/{provider}/models")
async def get_provider_models(provider: str, base_url: Optional[str] = None):
    """
    Get available models for a specific provider by calling list_available_models().
    Always fetches fresh list - no caching.

    Args:
        provider: Provider name (ollama, lmstudio, huggingface, etc.)
        base_url: Optional custom base URL for local providers (for testing connectivity)
    """
    # ============ DEBUG START - REMOVE AFTER TESTING ============
    logger.info(f"🔍 === get_provider_models ENTRY POINT ===")
    logger.info(f"   provider={provider} (type: {type(provider)})")
    logger.info(f"   base_url={base_url} (type: {type(base_url)})")
    if base_url:
        logger.info(f"   base_url length: {len(base_url)}")
        logger.info(f"   base_url stripped: '{base_url.strip()}'")
    # ============ DEBUG END ============

    logger.info(f"🔍 Fetching models for {provider}...")

    try:
        from abstractcore import create_llm
        from abstractcore.config import configure_provider
        from abstractcore.exceptions import ModelNotFoundError
        from ..services.user_settings_service import get_user_settings_service

        # Create LLM instance for this provider
        loop = asyncio.get_event_loop()

        def _get_models():
            # Always configure from user settings first
            # This ensures we use the saved base URL for the provider
            settings_service = get_user_settings_service()
            settings = settings_service.get_settings()

            # Get base URL from settings (unless overridden by parameter)
            url_to_use = base_url if base_url else settings.llm.base_urls.get(provider)

            logger.info(f"🔍 get_provider_models: provider={provider}, base_url_param={base_url}, url_from_settings={settings.llm.base_urls.get(provider)}, url_to_use={url_to_use}")

            if url_to_use and url_to_use.strip():
                configure_provider(provider, base_url=url_to_use)
                logger.info(f"📍 Configured {provider} with base_url: {url_to_use}")
            else:
                logger.warning(f"⚠️ No base_url configured for {provider}")

            # Try to create LLM and get models
            # Some providers (like LMStudio) raise ModelNotFoundError for invalid model names
            # but the error message contains the list of available models
            try:
                logger.info(f"🔨 Creating LLM instance: provider={provider}, model='dummy'")
                llm = create_llm(provider, model="dummy")
                logger.info(f"✅ LLM created. base_url={getattr(llm, 'base_url', 'unknown')}")

                logger.info(f"📞 Calling llm.list_available_models()...")
                models = llm.list_available_models()
                logger.info(f"✅ list_available_models() returned {len(models)} models")

                if len(models) == 0:
                    logger.warning(f"⚠️ ZERO MODELS RETURNED! This is the bug!")
                    logger.warning(f"   provider={provider}, base_url={getattr(llm, 'base_url', 'unknown')}")
                    # Try direct base_url parameter as fallback
                    if url_to_use:
                        logger.info(f"🔄 Retrying with direct base_url parameter...")
                        llm2 = create_llm(provider, model="dummy", base_url=url_to_use)
                        models2 = llm2.list_available_models()
                        logger.info(f"✅ Retry with base_url param returned {len(models2)} models")
                        return models2

                return models
            except ModelNotFoundError as e:
                # Parse available models from error message
                # Format: "Available models (N):\n  • model1\n  • model2\n..."
                error_msg = str(e)
                logger.info(f"⚠️ ModelNotFoundError: {error_msg[:200]}")
                if "Available models" in error_msg:
                    import re
                    # Extract models from bullet points
                    models = re.findall(r'  • (.+)', error_msg)
                    if models:
                        logger.info(f"✅ Parsed {len(models)} models from ModelNotFoundError")
                        return models
                # If we can't parse models, raise the error
                raise

        # Run in thread pool to avoid blocking
        models = await loop.run_in_executor(None, _get_models)

        logger.info(f"🏁 Found {len(models)} models for {provider}")

        # ============ DEBUG START - REMOVE AFTER TESTING ============
        # FIX: If 0 models returned, mark as unavailable (connection likely failed)
        is_available = len(models) > 0
        if not is_available:
            logger.warning(f"⚠️ Marking provider as unavailable (0 models found)")
        # ============ DEBUG END ============

        return {
            "provider": provider,
            "models": models,
            "count": len(models),
            "available": is_available  # True only if models were found
        }

    except Exception as e:
        logger.error(f"❌ Failed to get models for {provider}: {e}")
        return {
            "provider": provider,
            "models": [],
            "count": 0,
            "available": False,  # Connection failed
            "error": str(e)
        }


@router.post("/providers/select")
async def select_provider(request: ProviderSelectionRequest):
    """
    Select a provider and model for code generation.
    Updates global configuration and reinitializes the LLM.
    If notebook_id is provided, also updates that specific notebook's config.
    """
    try:
        # Save to project configuration
        config.set_llm_config(request.provider, request.model)

        # Update notebook service configuration
        notebook_service.llm_service.provider = request.provider
        notebook_service.llm_service.model = request.model
        notebook_service.llm_service._initialize_llm()

        logger.info(f"✅ LLM configured: {request.provider}/{request.model}")

        # If notebook_id provided, update that notebook's config too
        if request.notebook_id:
            try:
                notebook = notebook_service.get_notebook(request.notebook_id)
                if notebook:
                    notebook.llm_provider = request.provider
                    notebook.llm_model = request.model
                    notebook_service._save_notebook(notebook)
                    logger.info(f"✅ Updated notebook {request.notebook_id} config: {request.provider}/{request.model}")
            except Exception as nb_error:
                logger.warning(f"⚠️ Failed to update notebook config (non-critical): {nb_error}")
                # Don't fail the entire request if notebook update fails

        return {
            "success": True,
            "provider": request.provider,
            "model": request.model,
            "message": f"Successfully configured {request.provider} with model {request.model}"
        }

    except Exception as e:
        logger.error(f"❌ Failed to configure provider: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to configure provider: {str(e)}"
        )


@router.get("/config")
async def get_current_config():
    """Get the current global LLM configuration."""
    try:
        return {
            "provider": config.get_llm_provider(),
            "model": config.get_llm_model(),
            "config_file": str(CONFIG_FILE)
        }
    except Exception as e:
        logger.error(f"❌ Failed to get LLM config: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get LLM config: {str(e)}"
        )


@router.get("/status")
async def get_llm_status(notebook_id: Optional[str] = None):
    """
    Get detailed status of the currently active LLM.
    Returns provider, model, token configuration, and connection status.
    """
    try:
        llm_service = notebook_service.llm_service

        # Get provider/model from notebook if available, otherwise use global
        provider = llm_service.provider
        model = llm_service.model

        if notebook_id:
            notebook = notebook_service.get_notebook(notebook_id)
            if notebook:
                provider = notebook.llm_provider
                model = notebook.llm_model
                logger.info(f"📊 Using notebook-specific config: {provider}/{model}")

        status_info = {
            "provider": provider,
            "model": model,
            "status": "unknown",
            "max_tokens": None,
            "max_input_tokens": None,
            "max_output_tokens": None,
            "token_summary": None,
            "active_context_tokens": None
        }

        # Check provider health
        try:
            health_result = llm_service.check_provider_health()
            status_info["status"] = health_result["status"]
            if not health_result["healthy"]:
                status_info["error_message"] = health_result["message"]

            # Get token configuration
            if hasattr(llm_service, 'llm') and llm_service.llm is not None:
                llm = llm_service.llm
                status_info["max_tokens"] = getattr(llm, 'max_tokens', None)
                status_info["max_input_tokens"] = getattr(llm, 'max_input_tokens', None)
                status_info["max_output_tokens"] = getattr(llm, 'max_output_tokens', None)

                if hasattr(llm, 'get_token_configuration_summary'):
                    try:
                        status_info["token_summary"] = llm.get_token_configuration_summary()
                    except:
                        pass

        except Exception as health_error:
            status_info["status"] = "error"
            status_info["error_message"] = f"Health check failed: {str(health_error)}"
            logger.error(f"❌ LLM health check failed: {health_error}")

        # Get actual context tokens from last generation
        if notebook_id:
            try:
                actual_context_tokens = llm_service.token_tracker.get_current_context_tokens(notebook_id)

                if actual_context_tokens == 0:
                    notebook = notebook_service.get_notebook(notebook_id)
                    if notebook and hasattr(notebook, 'last_context_tokens') and notebook.last_context_tokens > 0:
                        actual_context_tokens = notebook.last_context_tokens
                        logger.info(f"📊 Using persisted context tokens for notebook {notebook_id}: {actual_context_tokens}")

                if actual_context_tokens > 0:
                    status_info["active_context_tokens"] = actual_context_tokens
                    logger.info(f"📊 Active context for notebook {notebook_id}: {actual_context_tokens} tokens")
            except Exception as context_error:
                logger.warning(f"Could not get context tokens: {context_error}")

        return status_info

    except Exception as e:
        logger.error(f"❌ Failed to get LLM status: {e}")
        return {
            "provider": config.get_llm_provider(),
            "model": config.get_llm_model(),
            "status": "error",
            "error_message": str(e),
            "max_tokens": None,
            "max_input_tokens": None,
            "max_output_tokens": None,
            "active_context_tokens": None
        }


@router.get("/debug/connection")
async def debug_ollama_connection(base_url: str):
    """
    Debug endpoint to test Ollama connection from backend.
    This helps diagnose issues with external Ollama instances in Docker deployments.

    Usage: GET /api/llm/debug/connection?base_url=http://172.20.10.2:11434
    """
    import socket
    import requests
    from urllib.parse import urlparse
    from abstractcore import create_llm
    from abstractcore.config import configure_provider

    results = {
        "base_url": base_url,
        "tests": {}
    }

    # Test 1: Network connectivity (TCP socket)
    try:
        parsed = urlparse(base_url)
        host = parsed.hostname
        port = parsed.port or 11434

        sock = socket.create_connection((host, port), timeout=3)
        sock.close()

        results["tests"]["tcp_connection"] = {
            "status": "success",
            "message": f"TCP connection to {host}:{port} successful"
        }
    except Exception as e:
        results["tests"]["tcp_connection"] = {
            "status": "failed",
            "error": str(e)
        }

    # Test 2: Direct HTTP request to Ollama API
    try:
        response = requests.get(f"{base_url}/api/tags", timeout=5)
        response.raise_for_status()
        data = response.json()
        model_count = len(data.get('models', []))

        results["tests"]["direct_api_call"] = {
            "status": "success",
            "model_count": model_count,
            "first_5_models": [m['name'] for m in data.get('models', [])[:5]]
        }
    except Exception as e:
        results["tests"]["direct_api_call"] = {
            "status": "failed",
            "error": str(e)
        }

    # Test 3: AbstractCore with configure_provider()
    try:
        configure_provider('ollama', base_url=base_url)
        llm = create_llm('ollama', model='dummy')
        models = llm.list_available_models()

        results["tests"]["abstractcore_configured"] = {
            "status": "success",
            "model_count": len(models),
            "first_5_models": models[:5] if models else [],
            "llm_base_url": getattr(llm, 'base_url', 'unknown')
        }
    except Exception as e:
        results["tests"]["abstractcore_configured"] = {
            "status": "failed",
            "error": str(e)
        }

    # Test 4: AbstractCore with direct base_url parameter
    try:
        llm = create_llm('ollama', model='dummy', base_url=base_url)
        models = llm.list_available_models()

        results["tests"]["abstractcore_direct"] = {
            "status": "success",
            "model_count": len(models),
            "first_5_models": models[:5] if models else [],
            "llm_base_url": getattr(llm, 'base_url', 'unknown')
        }
    except Exception as e:
        results["tests"]["abstractcore_direct"] = {
            "status": "failed",
            "error": str(e)
        }

    # Summary
    test_results = [t["status"] for t in results["tests"].values()]
    results["summary"] = {
        "total_tests": len(test_results),
        "passed": test_results.count("success"),
        "failed": test_results.count("failed")
    }

    return results
