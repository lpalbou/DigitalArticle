"""
API endpoints for LLM operations.

This module provides REST endpoints for LLM-related functionality
such as code generation, explanation, and provider management.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional

from ..services.shared import notebook_service
from ..config import config, CONFIG_FILE
from abstractcore import create_llm, ModelNotFoundError, ProviderAPIError, AuthenticationError
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


@router.get("/status")
async def get_llm_status():
    """Get the status of the LLM service."""
    try:
        return {
            "provider": llm_service.provider,
            "model": llm_service.model,
            "status": "ready" if llm_service.llm else "not_initialized"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get LLM status: {str(e)}"
        )


class ProviderInfo(BaseModel):
    """Information about an LLM provider."""
    name: str
    display_name: str
    available: bool
    error: Optional[str] = None
    default_model: Optional[str] = None
    models: List[str] = []


class ProviderSelectionRequest(BaseModel):
    """Request to set provider and model."""
    provider: str
    model: str


@router.get("/providers", response_model=List[ProviderInfo])
async def get_available_providers():
    """
    Get list of available LLM providers with their status and available models.

    Returns:
        List of providers with availability status
    """
    providers_to_check = [
        {"name": "lmstudio", "display_name": "LM Studio", "default": "qwen/qwen3-next-80b"},
        {"name": "ollama", "display_name": "Ollama", "default": "qwen3-coder:30b"},
        {"name": "anthropic", "display_name": "Anthropic (Claude)", "default": "claude-3-5-haiku-latest"},
        {"name": "openai", "display_name": "OpenAI (GPT)", "default": "gpt-4o-mini"},
        {"name": "mlx", "display_name": "MLX (Apple Silicon)", "default": "mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit"},
    ]

    results = []

    for provider_info in providers_to_check:
        provider_name = provider_info["name"]
        default_model = provider_info["default"]

        try:
            # Try to create an LLM instance with the default model
            llm = create_llm(provider_name, model=default_model)

            # Try to get available models dynamically
            models = []
            try:
                if hasattr(llm, 'list_available_models'):
                    models_list = llm.list_available_models()
                    if isinstance(models_list, list):
                        models = models_list[:20]  # Limit to first 20 models
                        logger.info(f"Retrieved {len(models)} models for {provider_name}")
                    else:
                        models = [default_model]
                else:
                    models = [default_model]
            except Exception as e:
                logger.warning(f"Could not list models for {provider_name}: {e}")
                models = [default_model]

            # If successful, provider is available
            results.append(ProviderInfo(
                name=provider_name,
                display_name=provider_info["display_name"],
                available=True,
                default_model=default_model,
                models=models if models else [default_model]
            ))

        except AuthenticationError as e:
            # Provider exists but needs API key
            results.append(ProviderInfo(
                name=provider_name,
                display_name=provider_info["display_name"],
                available=False,
                error=f"Authentication required: Set API key in environment",
                default_model=default_model,
                models=provider_info.get("models", [])
            ))

        except ModelNotFoundError as e:
            # Provider exists but model not found (still mark as potentially available)
            results.append(ProviderInfo(
                name=provider_name,
                display_name=provider_info["display_name"],
                available=False,
                error=f"Model not found. Provider may be offline or model not installed",
                default_model=default_model,
                models=provider_info.get("models", [])
            ))

        except ImportError as e:
            # Provider dependencies not installed
            results.append(ProviderInfo(
                name=provider_name,
                display_name=provider_info["display_name"],
                available=False,
                error="Dependencies not installed",
                default_model=default_model,
                models=[]
            ))

        except Exception as e:
            # Other errors (network, etc.)
            results.append(ProviderInfo(
                name=provider_name,
                display_name=provider_info["display_name"],
                available=False,
                error=str(e)[:100],  # Truncate long error messages
                default_model=default_model,
                models=provider_info.get("models", [])
            ))

    return results


@router.post("/providers/select")
async def select_provider(request: ProviderSelectionRequest):
    """
    Select a provider and model for code generation.

    This will update the global LLM service configuration and save to project config.

    Args:
        request: Provider and model selection

    Returns:
        Success status and configuration
    """
    try:
        # Save to project-level configuration FIRST
        config.set_llm_config(request.provider, request.model)

        # Update the notebook service's LLM configuration
        notebook_service.llm_service.provider = request.provider
        notebook_service.llm_service.model = request.model

        # CRITICAL: Reinitialize the LLM with new provider/model
        notebook_service.llm_service._initialize_llm()

        logger.info(f"✅ LLM configuration updated and reinitialized: {request.provider}/{request.model}")

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
    """
    Get the current global LLM configuration.

    Returns the currently configured provider and model from global config.
    """
    try:
        provider = config.get_llm_provider()
        model = config.get_llm_model()

        return {
            "provider": provider,
            "model": model,
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
    Get detailed status of the currently active LLM including token configuration.

    Returns provider, model, context size, and connection status.
    Optionally includes ACTUAL context tokens from last generation (via AbstractCore).

    Args:
        notebook_id: Optional notebook ID to get actual token usage

    Note:
        Uses ONLY AbstractCore's response.usage for token counts.
        NO estimation - only real data from LLM provider.
    """
    try:
        llm_service = notebook_service.llm_service

        # Get token configuration from the LLM instance
        status_info = {
            "provider": llm_service.provider,
            "model": llm_service.model,
            "status": "connected",
            "max_tokens": None,
            "max_input_tokens": None,
            "max_output_tokens": None,
            "token_summary": None,
            "active_context_tokens": None
        }

        # Try to get token configuration from the LLM instance
        try:
            if hasattr(llm_service, 'llm') and llm_service.llm is not None:
                llm = llm_service.llm
                status_info["max_tokens"] = getattr(llm, 'max_tokens', None)
                status_info["max_input_tokens"] = getattr(llm, 'max_input_tokens', None)
                status_info["max_output_tokens"] = getattr(llm, 'max_output_tokens', None)

                # Get formatted token summary if available
                if hasattr(llm, 'get_token_configuration_summary'):
                    try:
                        status_info["token_summary"] = llm.get_token_configuration_summary()
                    except:
                        pass
        except Exception as token_error:
            logger.warning(f"Could not get token configuration: {token_error}")

        # Get ACTUAL context tokens from last generation (via AbstractCore response.usage)
        if notebook_id:
            try:
                # Use TokenTracker to get real prompt_tokens from last generation
                actual_context_tokens = llm_service.token_tracker.get_current_context_tokens(notebook_id)
                if actual_context_tokens > 0:
                    status_info["active_context_tokens"] = actual_context_tokens
                    logger.info(f"📊 Active context for notebook {notebook_id}: {actual_context_tokens} tokens (from AbstractCore)")
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
