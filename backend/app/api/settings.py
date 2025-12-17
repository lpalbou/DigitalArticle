"""
User Settings API endpoints.

Provides per-user settings management for LLM configuration and reproducibility.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..services.user_settings_service import (
    get_user_settings_service,
    UserSettings,
    LLMSettings,
    ReproducibilitySettings,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/settings", tags=["settings"])


class LLMSettingsUpdate(BaseModel):
    """Request model for updating LLM settings."""
    provider: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    base_urls: Optional[Dict[str, str]] = None


class ReproducibilitySettingsUpdate(BaseModel):
    """Request model for updating reproducibility settings."""
    use_llm_seed: Optional[bool] = None
    llm_seed: Optional[int] = None
    use_code_seed: Optional[bool] = None
    code_seed: Optional[int] = None


class SettingsUpdateRequest(BaseModel):
    """Request model for updating user settings."""
    llm: Optional[LLMSettingsUpdate] = None
    reproducibility: Optional[ReproducibilitySettingsUpdate] = None


class ApiKeyUpdateRequest(BaseModel):
    """Request model for updating an API key."""
    provider: str
    api_key: str


class SettingsResponse(BaseModel):
    """Response model for settings (with masked API keys)."""
    llm: Dict[str, Any]
    reproducibility: Dict[str, Any]
    version: int


@router.get("", response_model=SettingsResponse)
async def get_settings():
    """
    Get current user settings.
    
    Returns settings with API keys masked for security.
    """
    try:
        service = get_user_settings_service()
        settings = service.get_settings_for_api()
        return SettingsResponse(**settings)
    except Exception as e:
        logger.error(f"Failed to get settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("", response_model=SettingsResponse)
async def update_settings(request: SettingsUpdateRequest):
    """
    Update user settings.
    
    Supports partial updates - only provided fields are changed.
    """
    try:
        service = get_user_settings_service()
        
        # Build updates dict from request
        updates = {}
        
        if request.llm:
            llm_updates = {}
            if request.llm.provider is not None:
                llm_updates['provider'] = request.llm.provider
            if request.llm.model is not None:
                llm_updates['model'] = request.llm.model
            if request.llm.temperature is not None:
                llm_updates['temperature'] = request.llm.temperature
            if request.llm.base_urls is not None:
                llm_updates['base_urls'] = request.llm.base_urls
            if llm_updates:
                updates['llm'] = llm_updates
        
        if request.reproducibility:
            repro_updates = {}
            if request.reproducibility.use_llm_seed is not None:
                repro_updates['use_llm_seed'] = request.reproducibility.use_llm_seed
            if request.reproducibility.llm_seed is not None:
                repro_updates['llm_seed'] = request.reproducibility.llm_seed
            if request.reproducibility.use_code_seed is not None:
                repro_updates['use_code_seed'] = request.reproducibility.use_code_seed
            if request.reproducibility.code_seed is not None:
                repro_updates['code_seed'] = request.reproducibility.code_seed
            if repro_updates:
                updates['reproducibility'] = repro_updates
        
        if updates:
            service.update_settings(updates)
            logger.info(f"Settings updated: {list(updates.keys())}")

            # CRITICAL: Reinitialize LLMService when LLM settings change
            # This ensures base_url changes take effect immediately (fixes remote deployment issue)
            llm_updates = updates.get('llm', {})
            if 'base_urls' in llm_updates or 'provider' in llm_updates or 'model' in llm_updates:
                try:
                    from ..services.shared import notebook_service
                    notebook_service.llm_service._initialize_llm()
                    logger.info("✅ LLMService reinitialized with new settings")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to reinitialize LLM (non-critical): {e}")

        # Return updated settings (with masked keys)
        settings = service.get_settings_for_api()
        return SettingsResponse(**settings)
        
    except Exception as e:
        logger.error(f"Failed to update settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/api-key")
async def update_api_key(request: ApiKeyUpdateRequest):
    """
    Update an API key for a specific provider.
    
    API keys are stored securely and never returned in plain text.
    """
    try:
        service = get_user_settings_service()
        
        valid_providers = ['openai', 'anthropic', 'huggingface']
        if request.provider not in valid_providers:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid provider. Must be one of: {valid_providers}"
            )
        
        service.set_api_key(request.provider, request.api_key)
        
        return {"status": "success", "provider": request.provider}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update API key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api-key/{provider}")
async def delete_api_key(provider: str):
    """Clear an API key for a specific provider."""
    try:
        service = get_user_settings_service()
        
        valid_providers = ['openai', 'anthropic', 'huggingface']
        if provider not in valid_providers:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid provider. Must be one of: {valid_providers}"
            )
        
        service.set_api_key(provider, "")
        
        return {"status": "success", "provider": provider}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete API key: {e}")
        raise HTTPException(status_code=500, detail=str(e))

