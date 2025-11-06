"""
API endpoints for notebook management.

This module provides REST endpoints for creating, reading, updating,
and deleting notebooks.
"""

from typing import List
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response

from ..models.notebook import (
    Notebook, NotebookCreateRequest, NotebookUpdateRequest, CellState
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


@router.get("/summaries")
async def list_notebook_summaries():
    """Get notebook summaries for browsing interface."""
    try:
        summaries = notebook_service.get_notebook_summaries()
        return summaries
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get notebook summaries: {str(e)}"
        )


@router.post("/{notebook_id}/cells/mark-stale")
async def mark_cells_as_stale(notebook_id: str, from_cell_index: int):
    """Mark all cells below the given index as stale."""
    try:
        success = notebook_service.mark_cells_as_stale(notebook_id, from_cell_index)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notebook not found"
            )
        return {"success": True, "message": f"Marked cells below index {from_cell_index} as stale"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark cells as stale: {str(e)}"
        )


@router.post("/{notebook_id}/cells/{cell_id}/mark-fresh")
async def mark_cell_as_fresh(notebook_id: str, cell_id: str):
    """Mark a specific cell as fresh."""
    try:
        success = notebook_service.mark_cell_as_fresh(notebook_id, cell_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notebook or cell not found"
            )
        return {"success": True, "message": f"Marked cell {cell_id} as fresh"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark cell as fresh: {str(e)}"
        )


@router.post("/{notebook_id}/cells/bulk-update-states")
async def bulk_update_cell_states(notebook_id: str, cell_updates: List[dict]):
    """Update multiple cell states in bulk."""
    try:
        success = notebook_service.bulk_update_cell_states(notebook_id, cell_updates)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notebook not found"
            )
        return {"success": True, "message": f"Updated {len(cell_updates)} cell states"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk update cell states: {str(e)}"
        )


@router.get("/{notebook_id}/cells/{cell_id}/cells-below")
async def get_cells_below(notebook_id: str, cell_id: str):
    """Get all cells below a specific cell."""
    try:
        # First get the cell index
        cell_index = notebook_service.get_cell_index(notebook_id, cell_id)
        if cell_index == -1:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cell not found"
            )
        
        # Get cells below this index
        cells_below = notebook_service.get_cells_below_index(notebook_id, cell_index)
        
        return {
            "cell_index": cell_index,
            "cells_below_count": len(cells_below),
            "cells_below": [{"id": str(cell.id), "cell_type": cell.cell_type} for cell in cells_below]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cells below: {str(e)}"
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
    if format not in ["json", "jsonld", "semantic", "html", "markdown", "pdf"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format must be one of: json, jsonld, semantic, html, markdown, pdf"
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
                "jsonld": "application/ld+json",
                "semantic": "application/ld+json",
                "html": "text/html",
                "markdown": "text/markdown"
            }[format]
            
            return Response(content=content, media_type=media_type)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export notebook: {str(e)}"
        )


@router.post("/{notebook_id}/seed")
async def set_notebook_seed(notebook_id: str, seed_data: dict):
    """Set custom seed for notebook reproducibility."""
    try:
        seed = seed_data.get("seed")
        if seed is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Seed value is required"
            )
        
        if not isinstance(seed, int) or seed < 0 or seed > 2147483647:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Seed must be an integer between 0 and 2,147,483,647"
            )
        
        success = notebook_service.set_notebook_custom_seed(notebook_id, seed)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notebook not found"
            )
        
        return {"message": "Seed set successfully", "seed": seed}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set seed: {str(e)}"
        )


@router.post("/{notebook_id}/generate-abstract")
async def generate_abstract(notebook_id: str):
    """Generate a scientific abstract for the entire digital article."""
    try:
        abstract = notebook_service.generate_abstract(notebook_id)
        return {"abstract": abstract}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate abstract: {str(e)}"
        )
