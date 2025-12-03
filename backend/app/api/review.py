"""
Review API endpoints for Digital Article.

Provides REST API for cell-level review, article-level review, and review settings.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, status

from ..models.review import CellReview, ArticleReview, ReviewSettings
from ..services.review_service import ReviewService
from ..services.shared import notebook_service

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

        # Run review
        cell_review = review_service.review_cell(cell, notebook, force=force)

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

        # Run article review
        article_review = review_service.review_article(notebook, force=force)

        # Save review to notebook metadata
        if 'article_review' not in notebook.metadata:
            notebook.metadata['article_review'] = {}
        notebook.metadata['article_review'] = article_review.model_dump()
        notebook_service._save_notebook(notebook)

        return article_review

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to review article: {str(e)}"
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
