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


@router.get("/providers", response_model=List[ProviderInfo])
async def get_available_providers():
    """
    Get list of available LLM providers (without models for speed).
    Use /providers/{provider}/models to get models for a specific provider.

    ALWAYS queries AbstractCore fresh - no caching.
    Sets API keys from settings as environment variables so AbstractCore sees them.
    """
    logger.info("🔍 Detecting available LLM providers...")

    # Get saved API keys and set as environment variables
    # This allows AbstractCore to see them when checking provider availability
    from ..services.user_settings_service import get_user_settings_service
    import os

    settings_service = get_user_settings_service()
    settings = settings_service.get_settings()

    # Set API keys in environment if they exist
    if settings.llm.api_keys.get('openai'):
        os.environ['OPENAI_API_KEY'] = settings.llm.api_keys['openai']
    if settings.llm.api_keys.get('anthropic'):
        os.environ['ANTHROPIC_API_KEY'] = settings.llm.api_keys['anthropic']
    if settings.llm.api_keys.get('huggingface'):
        os.environ['HUGGINGFACE_TOKEN'] = settings.llm.api_keys['huggingface']

    # Use AbstractCore's provider registry - get metadata only (no models)
    # This will now see the API keys we just set
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
        base_url: Optional custom base URL for local providers
    """
    logger.info(f"🔍 Fetching models for {provider}...")

    try:
        from abstractcore import create_llm

        # Create LLM instance for this provider
        loop = asyncio.get_event_loop()

        def _get_models():
            kwargs = {}
            if base_url:
                kwargs['base_url'] = base_url

            # Create temporary LLM instance
            llm = create_llm(provider, model="dummy", **kwargs)

            # Call list_available_models() - always fresh, no cache
            return llm.list_available_models()

        # Run in thread pool to avoid blocking
        models = await loop.run_in_executor(None, _get_models)

        logger.info(f"🏁 Found {len(models)} models for {provider}")

        return {
            "provider": provider,
            "models": models,
            "count": len(models)
        }

    except Exception as e:
        logger.error(f"❌ Failed to get models for {provider}: {e}")
        return {
            "provider": provider,
            "models": [],
            "count": 0,
            "error": str(e)
        }


@router.post("/providers/select")
async def select_provider(request: ProviderSelectionRequest):
    """
    Select a provider and model for code generation.
    Updates global configuration and reinitializes the LLM.
    """
    try:
        # Save to project configuration
        config.set_llm_config(request.provider, request.model)

        # Update notebook service configuration
        notebook_service.llm_service.provider = request.provider
        notebook_service.llm_service.model = request.model
        notebook_service.llm_service._initialize_llm()

        logger.info(f"✅ LLM configured: {request.provider}/{request.model}")

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
