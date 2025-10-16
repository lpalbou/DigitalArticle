"""
API endpoints for file management.

This module provides REST endpoints for listing and managing files
in notebook workspaces.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, status

from ..services.data_manager_clean import get_data_manager

router = APIRouter()


@router.get("/{notebook_id}", response_model=List[Dict[str, Any]])
async def list_notebook_files(notebook_id: str):
    """List all files available in a notebook's workspace."""
    try:
        # Get the data manager for this notebook
        data_manager = get_data_manager(notebook_id)
        files = data_manager.list_available_files()
        return files
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list files: {str(e)}"
        )
