"""
API endpoints for notebook management.

This module provides REST endpoints for creating, reading, updating,
and deleting notebooks.
"""

import json
import logging
from typing import List, AsyncGenerator, Any, Dict
from datetime import datetime
from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import Response, StreamingResponse

from ..models.notebook import (
    Notebook, NotebookCreateRequest, NotebookUpdateRequest, CellState
)
from ..services.shared import notebook_service

router = APIRouter()
logger = logging.getLogger(__name__)


def make_json_serializable(obj: Any) -> Any:
    """Convert objects to JSON-serializable format.

    Handles datetime objects, Pydantic models, and nested structures.
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [make_json_serializable(item) for item in obj]
    elif hasattr(obj, 'model_dump'):  # Pydantic model
        return make_json_serializable(obj.model_dump())
    elif hasattr(obj, 'dict'):  # Older Pydantic
        return make_json_serializable(obj.dict())
    else:
        return obj


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
    if format not in ["json", "jsonld", "semantic", "analysis", "profile", "html", "markdown", "pdf"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format must be one of: json, jsonld, semantic, analysis, profile, html, markdown, pdf"
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
                "analysis": "application/ld+json",
                "profile": "application/ld+json",
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


# ============================================================================
# EXPORT STREAMING ENDPOINTS (SSE)
# ============================================================================

@router.post("/{notebook_id}/export/semantic/stream")
async def stream_semantic_export(
    notebook_id: str,
    type: str = Query(..., regex="^(analysis|profile)$"),
    action: str = Query("download", regex="^(download|view)$"),
):
    """Stream semantic graph extraction progress via SSE.

    Args:
        notebook_id: Notebook UUID
        type: Graph type ('analysis' for LLM-based, 'profile' for regex-based)
        action: What to do with result ('download' or 'view')

    Returns:
        StreamingResponse with progress updates
    """
    async def generate() -> AsyncGenerator[str, None]:
        """Generate SSE progress updates."""
        try:
            logger.info(f"🔍 SSE: Starting semantic export for {notebook_id}, type={type}, action={action}")

            # Stage 1: Loading
            yield f"data: {json.dumps(make_json_serializable({'stage': 'loading', 'progress': 5, 'message': 'Loading notebook...'}))}\n\n"

            notebook = notebook_service.get_notebook(notebook_id)
            if not notebook:
                logger.error(f"❌ SSE: Notebook {notebook_id} not found")
                yield f"data: {json.dumps({'stage': 'error', 'message': 'Notebook not found'})}\n\n"
                return

            logger.info(f"✅ SSE: Loaded notebook '{notebook.title}'")

            # Stream extraction progress
            async for progress_data in notebook_service.export_semantic_streaming(notebook, type):
                logger.debug(f"📊 SSE: Progress update: stage={progress_data.get('stage')} progress={progress_data.get('progress')}%")
                serializable_data = make_json_serializable(progress_data)
                yield f"data: {json.dumps(serializable_data)}\n\n"

            logger.info(f"✅ SSE: Completed semantic export for {notebook_id}")

        except Exception as e:
            logger.error(f"❌ SSE: Error during semantic export: {e}")
            yield f"data: {json.dumps({'stage': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/{notebook_id}/export/pdf/stream")
async def stream_pdf_export(
    notebook_id: str,
    include_code: bool = Query(False),
):
    """Stream PDF generation progress via SSE.

    Args:
        notebook_id: Notebook UUID
        include_code: Whether to include code in PDF

    Returns:
        StreamingResponse with progress updates and final PDF
    """
    async def generate() -> AsyncGenerator[str, None]:
        """Generate SSE progress updates."""
        try:
            # Stage 1: Loading
            yield f"data: {json.dumps({'stage': 'loading', 'progress': 5, 'message': 'Loading notebook...'})}\n\n"

            notebook = notebook_service.get_notebook(notebook_id)
            if not notebook:
                yield f"data: {json.dumps({'stage': 'error', 'message': 'Notebook not found'})}\n\n"
                return

            # Stream PDF generation progress
            async for progress_data in notebook_service.export_pdf_streaming(notebook, include_code):
                serializable_data = make_json_serializable(progress_data)
                yield f"data: {json.dumps(serializable_data)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'stage': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


# ============================================================================
# STATE MANAGEMENT ENDPOINTS
# ============================================================================

@router.get("/{notebook_id}/state")
async def get_notebook_state_info(notebook_id: str):
    """
    Get information about saved execution state for a notebook.

    Returns metadata including:
    - When state was last saved
    - Number of variables in saved state
    - Size of state file
    - Whether state file exists

    This is useful for UI indicators showing state availability.
    """
    try:
        metadata = notebook_service.execution_service.state_persistence.get_state_metadata(notebook_id)

        if metadata is None:
            return {
                "has_saved_state": False,
                "message": "No saved state found for this notebook"
            }

        return {
            "has_saved_state": True,
            **metadata
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get state info: {str(e)}"
        )


@router.delete("/{notebook_id}/state")
async def clear_notebook_state(notebook_id: str):
    """
    Clear saved execution state for a notebook.

    This removes the saved state file, forcing a fresh execution environment
    on next access. Useful for troubleshooting or forcing re-execution.

    Note: This does NOT clear the in-memory state if the notebook is currently loaded.
    """
    try:
        cleared = notebook_service.execution_service.state_persistence.clear_notebook_state(notebook_id)

        if cleared:
            return {
                "success": True,
                "message": f"Cleared saved state for notebook {notebook_id}"
            }
        else:
            return {
                "success": False,
                "message": f"No saved state found for notebook {notebook_id}"
            }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear state: {str(e)}"
        )


@router.post("/{notebook_id}/state/restore")
async def force_state_restoration(notebook_id: str):
    """
    Force restoration of saved state for a notebook.

    This explicitly loads the saved state into memory, replacing any current
    in-memory state. Useful for manually triggering state restoration.
    """
    try:
        # Clear in-memory state first
        if notebook_id in notebook_service.execution_service.notebook_globals:
            del notebook_service.execution_service.notebook_globals[notebook_id]

        # Trigger state restoration by accessing globals
        notebook_service.execution_service._get_notebook_globals(notebook_id)

        # Check if state was actually restored
        has_state = notebook_service.execution_service.state_persistence.has_saved_state(notebook_id)

        if has_state:
            metadata = notebook_service.execution_service.state_persistence.get_state_metadata(notebook_id)
            return {
                "success": True,
                "message": "State restored successfully",
                "variable_count": metadata.get('variable_count') if metadata else 0
            }
        else:
            return {
                "success": False,
                "message": "No saved state found to restore"
            }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restore state: {str(e)}"
        )
