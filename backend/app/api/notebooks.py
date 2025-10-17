"""
API endpoints for notebook management.

This module provides REST endpoints for creating, reading, updating,
and deleting notebooks.
"""

from typing import List
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response

from ..models.notebook import (
    Notebook, NotebookCreateRequest, NotebookUpdateRequest
)
from ..services.shared import notebook_service

router = APIRouter()


@router.post("/", response_model=Notebook, status_code=status.HTTP_201_CREATED)
async def create_notebook(request: NotebookCreateRequest):
    """Create a new notebook."""
    try:
        notebook = notebook_service.create_notebook(request)
        return notebook
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create notebook: {str(e)}"
        )


@router.get("/", response_model=List[Notebook])
async def list_notebooks():
    """Get all notebooks."""
    try:
        notebooks = notebook_service.list_notebooks()
        return notebooks
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list notebooks: {str(e)}"
        )


@router.get("/{notebook_id}", response_model=Notebook)
async def get_notebook(notebook_id: str):
    """Get a specific notebook by ID."""
    notebook = notebook_service.get_notebook(notebook_id)
    if not notebook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Digital Article {notebook_id} not found"
        )
    return notebook


@router.put("/{notebook_id}", response_model=Notebook)
async def update_notebook(notebook_id: str, request: NotebookUpdateRequest):
    """Update a notebook."""
    notebook = notebook_service.update_notebook(notebook_id, request)
    if not notebook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Digital Article {notebook_id} not found"
        )
    return notebook


@router.delete("/{notebook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notebook(notebook_id: str):
    """Delete a notebook."""
    success = notebook_service.delete_notebook(notebook_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Digital Article {notebook_id} not found"
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{notebook_id}/export")
async def export_notebook(notebook_id: str, format: str = "json", include_code: bool = False):
    """Export a notebook in various formats."""
    if format not in ["json", "html", "markdown", "pdf"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format must be one of: json, html, markdown, pdf"
        )
    
    try:
        if format == "pdf":
            # Handle PDF export separately
            content = notebook_service.export_notebook_pdf(notebook_id, include_code)
            if content is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Digital Article {notebook_id} not found"
                )
            
            # Get notebook for filename
            notebook = notebook_service.get_notebook(notebook_id)
            filename = f"{notebook.title.replace(' ', '_')}.pdf" if notebook else f"notebook_{notebook_id}.pdf"
            
            return Response(
                content=content,
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        else:
            # Handle other formats
            content = notebook_service.export_notebook(notebook_id, format)
            if content is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Digital Article {notebook_id} not found"
                )
            
            media_type = {
                "json": "application/json",
                "html": "text/html",
                "markdown": "text/markdown"
            }[format]
            
            return Response(content=content, media_type=media_type)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export notebook: {str(e)}"
        )
