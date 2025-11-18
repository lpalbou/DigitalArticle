"""
API endpoints for cell management and execution.

This module provides REST endpoints for creating, updating, deleting,
and executing notebook cells.
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response
import logging

from ..models.notebook import (
    Cell, ExecutionResult, CellCreateRequest, CellUpdateRequest, CellExecuteRequest, CellExecuteResponse
)
from ..services.shared import notebook_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{cell_id}/status")
async def get_cell_status(cell_id: str):
    """
    Get the current status of a cell (including methodology writing status).

    Args:
        cell_id: Cell UUID

    Returns:
        Cell status information
    """
    try:
        cell = notebook_service.get_cell(cell_id)
        if not cell:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cell {cell_id} not found"
            )

        return {
            "cell_id": cell_id,
            "is_executing": cell.is_executing,
            "is_writing_methodology": cell.is_writing_methodology,
            "has_scientific_explanation": bool(cell.scientific_explanation),
            "scientific_explanation": cell.scientific_explanation
        }

    except Exception as e:
        logger.error(f"Error getting cell status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cell status: {str(e)}"
        )


@router.get("/{cell_id}/traces")
async def get_cell_traces(cell_id: str):
    """
    Get all LLM interaction traces for a cell (for observability).

    Retrieves traces from persistent storage (cell.llm_traces) first,
    falling back to AbstractCore's in-memory buffer if needed.

    Args:
        cell_id: Cell UUID

    Returns:
        List of trace objects with complete LLM interaction data
    """
    try:
        cell = notebook_service.get_cell(cell_id)
        if not cell:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cell {cell_id} not found"
            )

        # First, try to get traces from persistent storage (NEW: cell.llm_traces)
        if cell.llm_traces and len(cell.llm_traces) > 0:
            logger.info(f"Retrieved {len(cell.llm_traces)} persistent traces for cell {cell_id}")
            return {"cell_id": cell_id, "traces": cell.llm_traces, "source": "persistent"}

        # Fallback: Get traces from AbstractCore's in-memory buffer
        # (Only used for backward compatibility or if persistence failed)
        trace_ids = cell.metadata.get('trace_ids', [])

        if not trace_ids:
            logger.info(f"No traces found for cell {cell_id}")
            return {"cell_id": cell_id, "traces": [], "source": "none"}

        # Get traces from AbstractCore's LLM provider
        llm = notebook_service.llm_service.llm
        if not llm or not hasattr(llm, 'get_traces'):
            logger.warning("LLM provider does not support tracing")
            return {"cell_id": cell_id, "traces": [], "source": "unsupported"}

        # Fetch each trace by ID from in-memory buffer
        traces = []
        for trace_id in trace_ids:
            try:
                trace = llm.get_traces(trace_id=trace_id)
                if trace:
                    # Handle both dict and list returns
                    if isinstance(trace, dict):
                        traces.append(trace)
                    elif isinstance(trace, list) and len(trace) > 0:
                        traces.append(trace[0])
            except Exception as e:
                logger.warning(f"Failed to get trace {trace_id} from buffer: {e}")
                continue

        logger.info(f"Retrieved {len(traces)} traces from in-memory buffer for cell {cell_id}")
        return {"cell_id": cell_id, "traces": traces, "source": "in_memory"}

    except Exception as e:
        logger.error(f"Error getting cell traces: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cell traces: {str(e)}"
        )


@router.post("/", response_model=Cell, status_code=status.HTTP_201_CREATED)
async def create_cell(request: CellCreateRequest):
    """Create a new cell in a notebook."""
    try:
        cell = notebook_service.create_cell(request)
        if not cell:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Digital Article {request.notebook_id} not found"
            )
        return cell
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create cell: {str(e)}"
        )


@router.put("/{notebook_id}/{cell_id}", response_model=Cell)
async def update_cell(notebook_id: str, cell_id: str, request: CellUpdateRequest):
    """Update a cell."""
    try:
        cell = notebook_service.update_cell(notebook_id, cell_id, request)
        if not cell:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cell {cell_id} not found in notebook {notebook_id}"
            )
        return cell
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update cell: {str(e)}"
        )


@router.delete("/{notebook_id}/{cell_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cell(notebook_id: str, cell_id: str):
    """Delete a cell from a notebook."""
    try:
        success = notebook_service.delete_cell(notebook_id, cell_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cell {cell_id} not found in notebook {notebook_id}"
            )
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete cell: {str(e)}"
        )


@router.post("/execute", response_model=CellExecuteResponse)
async def execute_cell(request: CellExecuteRequest):
    """Execute a cell (generate code from prompt if needed and run it)."""
    try:
        logger.info(f"🚀 API: Executing cell: {request.cell_id}")
        logger.info(f"🚀 API: Force regenerate: {request.force_regenerate}")
        execution_result = notebook_service.execute_cell(request)
        if not execution_result:
            logger.error(f"🚀 API: Cell {request.cell_id} not found in notebook service")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cell {request.cell_id} not found"
            )
        
        cell, result = execution_result
        logger.info(f"🚀 API: Cell execution completed with status: {result.status}")
        logger.info(f"🚀 API: Scientific explanation length: {len(cell.scientific_explanation) if cell.scientific_explanation else 0}")
        return CellExecuteResponse(cell=cell, result=result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cell execution failed with exception: {e}")
        import traceback
        full_traceback = traceback.format_exc()
        logger.error(f"Full traceback: {full_traceback}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute cell: {str(e)}\n\nFull traceback:\n{full_traceback}"
        )


@router.get("/{notebook_id}/{cell_id}/variables")
async def get_cell_variables(notebook_id: str, cell_id: str):
    """Get information about variables in the execution context."""
    try:
        # Check if cell exists
        notebook = notebook_service.get_notebook(notebook_id)
        if not notebook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Digital Article {notebook_id} not found"
            )

        # Convert cell_id string to UUID for lookup
        from uuid import UUID
        try:
            cell_uuid = UUID(cell_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid cell ID format: {cell_id}"
            )

        cell = notebook.get_cell(cell_uuid)
        if not cell:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cell {cell_id} not found"
            )

        # Get variable information from execution service (notebook-specific)
        variables = notebook_service.execution_service.get_variable_info(notebook_id)
        return {"variables": variables}

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get variables: {str(e)}"
        )


@router.post("/{notebook_id}/clear")
async def clear_execution_context(notebook_id: str):
    """Clear the execution context for a notebook."""
    try:
        # Check if notebook exists
        notebook = notebook_service.get_notebook(notebook_id)
        if not notebook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Digital Article {notebook_id} not found"
            )
        
        # Clear the execution namespace for this specific notebook
        notebook_service.execution_service.clear_namespace(notebook_id)

        return {"message": f"Execution context cleared for notebook {notebook_id}"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear execution context: {str(e)}"
        )
