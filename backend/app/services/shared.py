"""
Shared service instances to ensure consistency across API endpoints.

This module provides singleton service instances that are shared
across all API endpoints to prevent state isolation issues.
"""

from .notebook_service import NotebookService

# Shared service instances
notebook_service = NotebookService()

__all__ = ["notebook_service"]
