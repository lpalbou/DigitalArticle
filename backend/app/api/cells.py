"""
API endpoints for cell management and execution.

This module provides REST endpoints for creating, updating, deleting,
and executing notebook cells.
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response

from ..models.notebook import (
    Cell, ExecutionResult, CellCreateRequest, CellUpdateRequest, CellExecuteRequest
)
from ..services.shared import notebook_service

router = APIRouter()


@router.post("/", response_model=Cell, status_code=status.HTTP_201_CREATED)
async def create_cell(request: CellCreateRequest):
    """Create a new cell in a notebook."""
    try:
        cell = notebook_service.create_cell(request)
        if not cell:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Notebook {request.notebook_id} not found"
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


@router.post("/execute", response_model=ExecutionResult)
async def execute_cell(request: CellExecuteRequest):
    """Execute a cell (generate code from prompt if needed and run it)."""
    try:
        logger.info(f"Executing cell: {request.cell_id}")
        result = notebook_service.execute_cell(request)
        if not result:
            logger.error(f"Cell {request.cell_id} not found in notebook service")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cell {request.cell_id} not found"
            )
        logger.info(f"Cell execution completed with status: {result.status}")
        return result
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
                detail=f"Notebook {notebook_id} not found"
            )
        
        cell = notebook.get_cell(cell_id)
        if not cell:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cell {cell_id} not found"
            )
        
        # Get variable information from execution service
        variables = notebook_service.execution_service.get_variable_info()
        return {"variables": variables}
        
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
                detail=f"Notebook {notebook_id} not found"
            )
        
        # Clear the execution namespace
        notebook_service.execution_service.clear_namespace()
        
        return {"message": "Execution context cleared"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear execution context: {str(e)}"
        )
