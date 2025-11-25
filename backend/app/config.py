"""
Configuration management for Digital Article.

Handles saving and loading project-level configuration including LLM provider settings.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Config file path at project root
CONFIG_FILE = Path(__file__).parent.parent.parent / "config.json"


class Config:
    """Project-level configuration manager."""

    def __init__(self):
        self.data = self.load()

    def load(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
                return self._default_config()
        else:
            return self._default_config()

    def save(self) -> None:
        """Save configuration to file."""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.data, f, indent=2)
            logger.info(f"Configuration saved to {CONFIG_FILE}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    def _default_config(self) -> Dict[str, Any]:
        """Return default configuration."""
        return {
            "llm": {
                "provider": "lmstudio",
                "model": "qwen/qwen3-next-80b"
            }
        }

    def get_llm_provider(self) -> str:
        """Get configured LLM provider."""
        return self.data.get("llm", {}).get("provider", "lmstudio")

    def get_llm_model(self) -> str:
        """Get configured LLM model."""
        return self.data.get("llm", {}).get("model", "qwen/qwen3-next-80b")

    def set_llm_config(self, provider: str, model: str) -> None:
        """Set LLM provider and model."""
        if "llm" not in self.data:
            self.data["llm"] = {}
        self.data["llm"]["provider"] = provider
        self.data["llm"]["model"] = model
        self.save()

    def get_notebooks_dir(self) -> str:
        """Get notebooks directory path (ENV > config.json > default)."""
        # Environment variable takes precedence
        env_path = os.getenv('NOTEBOOKS_DIR')
        if env_path:
            return env_path

        # Config file second
        config_path = self.data.get('paths', {}).get('notebooks_dir')
        if config_path:
            return config_path

        # Default last
        return 'notebooks'

    def get_workspace_root(self) -> str:
        """Get workspace root directory (ENV > config.json > default)."""
        # Environment variable takes precedence
        env_path = os.getenv('WORKSPACE_DIR')
        if env_path:
            return env_path

        # Config file second
        config_path = self.data.get('paths', {}).get('workspace_dir')
        if config_path:
            return config_path

        # Default last
        return 'backend/notebook_workspace'

    def set_paths(self, notebooks_dir: str = None, workspace_dir: str = None) -> None:
        """Set custom paths in config.json."""
        if 'paths' not in self.data:
            self.data['paths'] = {}

        if notebooks_dir:
            self.data['paths']['notebooks_dir'] = notebooks_dir
        if workspace_dir:
            self.data['paths']['workspace_dir'] = workspace_dir

        self.save()


# Global config instance
config = Config()
