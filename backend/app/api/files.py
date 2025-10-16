"""
API endpoints for file management.

This module provides REST endpoints for listing and managing files
in notebook workspaces.
"""

import os
import mimetypes
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, status, UploadFile, File
from fastapi.responses import Response
from pydantic import BaseModel

from ..services.data_manager_clean import get_data_manager

router = APIRouter()


class FileContentResponse(BaseModel):
    content: str
    content_type: str
    size: int


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


@router.get("/{notebook_id}/content", response_model=FileContentResponse)
async def get_file_content(notebook_id: str, file_path: str):
    """Get the content of a specific file in the notebook's workspace."""
    try:
        # Get the data manager for this notebook
        data_manager = get_data_manager(notebook_id)
        
        # Get the full path to the file
        workspace_path = data_manager.get_workspace_path()
        full_file_path = os.path.join(workspace_path, file_path)
        
        # Security check: ensure the file is within the workspace
        if not os.path.abspath(full_file_path).startswith(os.path.abspath(workspace_path)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: file is outside workspace"
            )
        
        # Check if file exists
        if not os.path.exists(full_file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {file_path}"
            )
        
        # Get file info
        file_size = os.path.getsize(full_file_path)
        content_type, _ = mimetypes.guess_type(full_file_path)
        
        # For very large files, limit the content we read
        max_size = 10 * 1024 * 1024  # 10MB limit
        if file_size > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large: {file_size} bytes (max: {max_size} bytes)"
            )
        
        # Determine encoding based on content type
        encoding = 'utf-8'
        if content_type and content_type.startswith('image/'):
            # For images, we'll return base64 encoded content
            import base64
            with open(full_file_path, 'rb') as f:
                content = base64.b64encode(f.read()).decode('utf-8')
            content_type = content_type or 'application/octet-stream'
        else:
            # For text files, try to read as UTF-8
            try:
                with open(full_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                content_type = content_type or 'text/plain'
            except UnicodeDecodeError:
                # If UTF-8 fails, try with latin-1 or return as binary
                try:
                    with open(full_file_path, 'r', encoding='latin-1') as f:
                        content = f.read()
                    content_type = 'text/plain; charset=latin-1'
                except Exception:
                    # Last resort: read as binary and base64 encode
                    import base64
                    with open(full_file_path, 'rb') as f:
                        content = base64.b64encode(f.read()).decode('utf-8')
                    content_type = 'application/octet-stream'
        
        return FileContentResponse(
            content=content,
            content_type=content_type,
            size=file_size
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read file: {str(e)}"
        )


@router.post("/{notebook_id}/upload", response_model=List[Dict[str, Any]])
async def upload_file(notebook_id: str, file: UploadFile = File(...)):
    """Upload a file to the notebook's workspace."""
    try:
        # Get the data manager for this notebook
        data_manager = get_data_manager(notebook_id)
        
        # Read file content
        content = await file.read()
        
        # Upload file using data manager
        files = data_manager.upload_file(file.filename, content)
        
        return files
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}"
        )


@router.delete("/{notebook_id}/{file_name}")
async def delete_file(notebook_id: str, file_name: str):
    """Delete a file from the notebook's workspace."""
    try:
        # Get the data manager for this notebook
        data_manager = get_data_manager(notebook_id)
        
        # Delete file using data manager
        success = data_manager.delete_file(file_name)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {file_name}"
            )
        
        return {"message": f"File {file_name} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete file: {str(e)}"
        )
