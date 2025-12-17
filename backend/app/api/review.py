"""
Review API endpoints for Digital Article.

Provides REST API for cell-level review, article-level review, and review settings.
"""

import json
import logging
from datetime import datetime
from typing import Optional, AsyncGenerator, Any, Dict
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from ..models.review import CellReview, ArticleReview, ReviewSettings
from ..services.review_service import ReviewService
from ..services.shared import notebook_service

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

# Initialize router
router = APIRouter(prefix="/api/review", tags=["review"])

# Initialize review service (get llm_service from notebook_service)
review_service = ReviewService(notebook_service.llm_service)


@router.post("/cell", response_model=CellReview)
async def review_cell_endpoint(
    notebook_id: str,
    cell_id: str,
    force: bool = False,
):
    """Trigger review for a single cell.

    Args:
        notebook_id: Notebook UUID
        cell_id: Cell UUID
        force: Force review even if cached review exists

    Returns:
        Cell review with findings
    """
    try:
        # Load notebook
        notebook = notebook_service.get_notebook(notebook_id)

        # Find cell
        cell = None
        for c in notebook.cells:
            if str(c.id) == cell_id:
                cell = c
                break

        if not cell:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cell {cell_id} not found in notebook {notebook_id}"
            )

        # Run review (async for multi-user support)
        cell_review = await review_service.review_cell(cell, notebook, force=force)

        # Save review to cell metadata
        cell.metadata['review'] = cell_review.model_dump()
        notebook_service._save_notebook(notebook)

        return cell_review

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to review cell: {str(e)}"
        )


@router.post("/article/{notebook_id}", response_model=ArticleReview)
async def review_article_endpoint(
    notebook_id: str,
    force: bool = False,
):
    """Trigger full article synthesis review.

    Args:
        notebook_id: Notebook UUID
        force: Force review even if cached review exists

    Returns:
        Article review with overall assessment, strengths, issues, and recommendations
    """
    try:
        # Load notebook
        notebook = notebook_service.get_notebook(notebook_id)

        # Run article review (async for multi-user support - returns tuple: review, trace)
        article_review, review_trace = await review_service.review_article(notebook, force=force)

        # Save review to notebook metadata (replace old review)
        notebook.metadata['article_review'] = article_review.model_dump()

        # Save trace to notebook metadata (replace old trace, not append)
        if review_trace:
            # Add timestamp if missing
            if 'timestamp' not in review_trace or review_trace['timestamp'] is None:
                from datetime import datetime
                review_trace['timestamp'] = datetime.now().isoformat()

            # Check if trace indicates an error
            is_error = review_trace.get('status') == 'error'

            # Only keep the LATEST review trace, not the entire history
            notebook.metadata['review_traces'] = [review_trace]

            # If error trace, log it but don't raise (trace is saved)
            if is_error:
                logger.warning(f"⚠️ Review completed with error: {review_trace.get('error_type')}")
                logger.warning(f"   Message: {review_trace.get('error_message')}")

        notebook_service._save_notebook(notebook)

        return article_review

    except Exception as e:
        # This should rarely happen now (errors are caught in review_service)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to review article: {str(e)}"
        )


@router.post("/article/{notebook_id}/stream")
async def review_article_stream(
    notebook_id: str,
    force: bool = False,
):
    """Stream article review progress via Server-Sent Events (SSE).

    Returns a stream of progress updates including:
    - Stage: preparing, building_context, reviewing, parsing, complete, error
    - Progress: 0-100 percentage
    - Message: Human-readable status message
    - Tokens: Token count during LLM generation (reviewing stage)
    - Review: Final review object (complete stage)

    Args:
        notebook_id: Notebook UUID
        force: Force review even if cached review exists

    Returns:
        StreamingResponse with SSE format (text/event-stream)
    """

    async def generate_progress() -> AsyncGenerator[str, None]:
        """Generate SSE progress updates."""
        try:
            # Stage 1: Preparing
            yield f"data: {json.dumps({'stage': 'preparing', 'progress': 5, 'message': 'Loading notebook...'})}\n\n"

            notebook = notebook_service.get_notebook(notebook_id)
            if not notebook:
                yield f"data: {json.dumps({'stage': 'error', 'message': 'Notebook not found'})}\n\n"
                return

            # Stage 2: Building context
            yield f"data: {json.dumps({'stage': 'building_context', 'progress': 15, 'message': 'Building article context...'})}\n\n"

            # Stage 3: LLM Review with streaming (main work)
            yield f"data: {json.dumps({'stage': 'reviewing', 'progress': 25, 'message': 'AI reviewer analyzing article...'})}\n\n"

            # Call review service with streaming - this yields progress updates
            final_review = None
            final_trace = None

            async for progress_data in review_service.review_article_streaming(notebook, force):
                # Make data JSON-serializable (handles datetime objects)
                serializable_data = make_json_serializable(progress_data)

                # Forward progress from review service
                yield f"data: {json.dumps(serializable_data)}\n\n"

                # Capture final review object
                if progress_data.get('stage') == 'complete' and 'review' in progress_data:
                    final_review = progress_data['review']
                    final_trace = progress_data.get('trace')

            # Save review to notebook metadata
            if final_review:
                notebook.metadata['article_review'] = final_review

                # Save trace if available
                if final_trace:
                    if 'timestamp' not in final_trace or final_trace['timestamp'] is None:
                        from datetime import datetime
                        final_trace['timestamp'] = datetime.now().isoformat()

                    notebook.metadata['review_traces'] = [final_trace]

                notebook_service._save_notebook(notebook)
                logger.info(f"✅ Article review complete and saved for notebook {notebook_id}")

        except Exception as e:
            logger.error(f"❌ Error during review streaming: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            yield f"data: {json.dumps({'stage': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate_progress(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@router.get("/notebooks/{notebook_id}/settings", response_model=ReviewSettings)
async def get_review_settings(notebook_id: str):
    """Get review settings for a notebook.

    Args:
        notebook_id: Notebook UUID

    Returns:
        Review settings (or default if not set)
    """
    try:
        # Load notebook
        notebook = notebook_service.get_notebook(notebook_id)

        # Get review settings from metadata
        settings_data = notebook.metadata.get('review_settings')

        if not settings_data:
            # Return default settings
            return ReviewSettings(
                auto_review_enabled=False,
                phases={
                    'intent_enabled': True,
                    'implementation_enabled': True,
                    'results_enabled': True,
                },
                display={
                    'show_severity': 'all',
                    'auto_collapse': False,
                    'show_suggestions': True,
                },
                review_style='constructive',
            )

        return ReviewSettings(**settings_data)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load review settings: {str(e)}"
        )


@router.put("/notebooks/{notebook_id}/settings", response_model=ReviewSettings)
async def update_review_settings(
    notebook_id: str,
    settings: ReviewSettings,
):
    """Update review settings for a notebook.

    Args:
        notebook_id: Notebook UUID
        settings: Review settings to save

    Returns:
        Updated review settings
    """
    try:
        # Load notebook
        notebook = notebook_service.get_notebook(notebook_id)

        # Update metadata
        notebook.metadata['review_settings'] = settings.model_dump()

        # Save notebook
        notebook_service._save_notebook(notebook)

        return settings

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update review settings: {str(e)}"
        )


@router.get("/notebooks/{notebook_id}/traces")
async def get_review_traces(notebook_id: str):
    """Get LLM traces for article review.

    Args:
        notebook_id: Notebook UUID

    Returns:
        Dictionary with traces list and source indicator
    """
    try:
        # Load notebook
        notebook = notebook_service.get_notebook(notebook_id)

        # Get traces from metadata
        traces = notebook.metadata.get('review_traces', [])

        return {
            "notebook_id": notebook_id,
            "traces": traces,
            "source": "persistent"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load review traces: {str(e)}"
        )
