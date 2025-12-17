"""
User Settings Service for Digital Article.

Stores per-user settings in JSON files based on Unix username.
Settings include LLM configuration, reproducibility options, and provider credentials.
"""

import getpass
import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from ..config import DEFAULT_LLM_PROVIDER, DEFAULT_LLM_MODEL

logger = logging.getLogger(__name__)


class LLMSettings(BaseModel):
    """LLM configuration settings."""
    provider: str = DEFAULT_LLM_PROVIDER
    model: str = DEFAULT_LLM_MODEL
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    base_urls: Dict[str, str] = Field(default_factory=lambda: {
        "ollama": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        "lmstudio": os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1"),
        "vllm": os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1"),
        "openai-compatible": os.getenv("OPENAI_COMPATIBLE_BASE_URL", "http://localhost:1234/v1"),
        "openai": "",  # Empty = use default OpenAI API
        "anthropic": "",  # Empty = use default Anthropic API
    })
    # API keys are stored but never returned to frontend in plain text
    api_keys: Dict[str, str] = Field(default_factory=lambda: {
        "openai": "",
        "anthropic": "",
        "huggingface": "",
    })


class ReproducibilitySettings(BaseModel):
    """Reproducibility configuration settings."""
    use_llm_seed: bool = True
    llm_seed: Optional[int] = None
    use_code_seed: bool = True
    code_seed: Optional[int] = None


class UserSettings(BaseModel):
    """Complete user settings schema."""
    llm: LLMSettings = Field(default_factory=LLMSettings)
    reproducibility: ReproducibilitySettings = Field(default_factory=ReproducibilitySettings)
    version: int = 1  # For future migrations


class UserSettingsService:
    """
    Manages per-user settings storage.
    
    Settings are stored in: {workspace}/user_settings/{username}.json
    """

    def __init__(self, workspace_root: Optional[str] = None):
        """Initialize the service with optional custom workspace."""
        if workspace_root is None:
            from ..config import config
            workspace_root = config.get_workspace_root()

        # Convert to absolute path if relative
        if not os.path.isabs(workspace_root):
            project_root = Path(__file__).parent.parent.parent.parent
            self.workspace_root = project_root / workspace_root
        else:
            self.workspace_root = Path(workspace_root)

        self.settings_dir = self.workspace_root / "user_settings"
        self.settings_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"UserSettingsService initialized: {self.settings_dir}")

    def _get_username(self) -> str:
        """Get current Unix username."""
        try:
            return getpass.getuser()
        except Exception:
            return os.environ.get('USER') or os.environ.get('USERNAME') or 'default'

    def _get_settings_path(self, username: Optional[str] = None) -> Path:
        """Get path to user's settings file."""
        if username is None:
            username = self._get_username()
        return self.settings_dir / f"{username}.json"

    def get_settings(self, username: Optional[str] = None) -> UserSettings:
        """
        Load user settings from file.
        
        Returns default settings if file doesn't exist.
        """
        settings_path = self._get_settings_path(username)
        
        if settings_path.exists():
            try:
                with open(settings_path, 'r') as f:
                    data = json.load(f)
                    settings = UserSettings(**data)
                    logger.debug(f"Loaded settings for user: {username or self._get_username()}")
                    return settings
            except Exception as e:
                logger.error(f"Failed to load user settings: {e}")
                return UserSettings()
        else:
            logger.debug(f"No settings file found, returning defaults for: {username or self._get_username()}")
            return UserSettings()

    def save_settings(self, settings: UserSettings, username: Optional[str] = None) -> None:
        """Save user settings to file."""
        settings_path = self._get_settings_path(username)
        
        try:
            with open(settings_path, 'w') as f:
                json.dump(settings.model_dump(), f, indent=2)
            logger.info(f"Saved settings for user: {username or self._get_username()}")
        except Exception as e:
            logger.error(f"Failed to save user settings: {e}")
            raise

    def update_settings(self, updates: Dict[str, Any], username: Optional[str] = None) -> UserSettings:
        """
        Partially update user settings.
        
        Merges updates with existing settings.
        """
        current = self.get_settings(username)
        current_dict = current.model_dump()
        
        # Deep merge updates
        self._deep_merge(current_dict, updates)
        
        # Validate and save
        updated = UserSettings(**current_dict)
        self.save_settings(updated, username)
        
        return updated

    def _deep_merge(self, base: Dict, updates: Dict) -> None:
        """Deep merge updates into base dict."""
        for key, value in updates.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def get_settings_for_api(self, username: Optional[str] = None) -> Dict[str, Any]:
        """
        Get settings formatted for API response.
        
        Masks API keys for security.
        """
        settings = self.get_settings(username)
        data = settings.model_dump()
        
        # Mask API keys - show only if set (as boolean)
        if 'llm' in data and 'api_keys' in data['llm']:
            for key in data['llm']['api_keys']:
                if data['llm']['api_keys'][key]:
                    data['llm']['api_keys'][key] = "***SET***"
                else:
                    data['llm']['api_keys'][key] = ""
        
        return data

    def set_api_key(self, provider: str, api_key: str, username: Optional[str] = None) -> None:
        """Set API key for a specific provider."""
        settings = self.get_settings(username)
        
        if provider in settings.llm.api_keys:
            settings.llm.api_keys[provider] = api_key
            self.save_settings(settings, username)
            logger.info(f"Updated {provider} API key for user: {username or self._get_username()}")
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def get_api_key(self, provider: str, username: Optional[str] = None) -> str:
        """Get API key for a specific provider (for internal use only)."""
        settings = self.get_settings(username)
        return settings.llm.api_keys.get(provider, "")

    def apply_env_var_overrides(self, username: Optional[str] = None) -> None:
        """
        Apply Docker ENV variable overrides to settings.

        Called at startup to ensure Docker-provided base URLs take priority
        over stale saved settings from previous runs.

        Only applies if env vars are actually set (non-empty).
        """
        env_base_urls = {
            'ollama': os.getenv('OLLAMA_BASE_URL', ''),
            'lmstudio': os.getenv('LMSTUDIO_BASE_URL', ''),
            'vllm': os.getenv('VLLM_BASE_URL', ''),
            'openai-compatible': os.getenv('OPENAI_COMPATIBLE_BASE_URL', ''),
        }

        # Only apply if at least one env var is set AND differs from localhost default
        # This distinguishes Docker deployment from local development
        env_vars_with_values = {k: v for k, v in env_base_urls.items() if v and 'localhost' not in v}

        if not env_vars_with_values:
            logger.debug("No Docker ENV var overrides to apply (using saved or default settings)")
            return

        # Get current settings
        settings = self.get_settings(username)

        # Override base URLs with env vars
        for provider, url in env_vars_with_values.items():
            old_url = settings.llm.base_urls.get(provider, '')
            if old_url != url:
                settings.llm.base_urls[provider] = url
                logger.info(f"🐳 Docker ENV override: {provider} base_url = {url}")

        # Save updated settings
        self.save_settings(settings, username)
        logger.info("✅ Applied Docker ENV var base URLs to settings")


# Global service instance
_user_settings_service: Optional[UserSettingsService] = None


def get_user_settings_service() -> UserSettingsService:
    """Get or create the global UserSettingsService instance."""
    global _user_settings_service
    if _user_settings_service is None:
        _user_settings_service = UserSettingsService()
    return _user_settings_service

