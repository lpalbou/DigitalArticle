"""
Shared service instances to ensure consistency across API endpoints.

This module provides singleton service instances that are shared
across all API endpoints to prevent state isolation issues.
"""

from .notebook_service import NotebookService
from ..config import config

# Initialize with configured paths (ENV > config.json > default)
notebooks_dir = config.get_notebooks_dir()
notebook_service = NotebookService(notebooks_dir=notebooks_dir)

__all__ = ["notebook_service"]
