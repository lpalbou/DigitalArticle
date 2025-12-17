"""
API endpoints for chat functionality.

This module provides REST endpoints for asking questions about Digital Articles
without modifying any content (read-only access).
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
import logging

from ..services.shared import notebook_service
from ..services.chat_service import ArticleChatService

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize chat service (uses LLM service from notebook_service)
chat_service = ArticleChatService(notebook_service)


class ChatMessage(BaseModel):
    """A single message in the conversation."""
    id: Optional[str] = None  # Frontend sends message ID
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: str
    loading: Optional[bool] = None  # Frontend sends loading state


class ChatRequest(BaseModel):
    """Request to ask a question about an article."""
    notebook_id: str
    message: str
    conversation_history: Optional[List[ChatMessage]] = []
    mode: str = 'article'  # 'article' or 'reviewer'


class ChatResponse(BaseModel):
    """Response with answer about the article."""
    message: str
    context_used: List[str]  # Cell IDs or data sources referenced
    timestamp: str


@router.post("/ask", response_model=ChatResponse)
async def ask_about_article(request: ChatRequest):
    """
    Answer questions about the Digital Article content.

    This endpoint:
    1. Retrieves notebook data (read-only)
    2. Builds context from cells (prompts, code, results, methodology)
    3. Sends question + context to LLM
    4. Returns conversational answer

    Args:
        request: Chat request with notebook_id, message, and optional history

    Returns:
        ChatResponse with answer and context references

    Raises:
        404: If notebook not found
        500: If chat service fails
    """
    try:
        # Validate notebook exists
        notebook = notebook_service.get_notebook(request.notebook_id)
        if not notebook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Notebook {request.notebook_id} not found"
            )

        # Convert conversation history to dict format
        history = [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp
            }
            for msg in request.conversation_history
        ] if request.conversation_history else []

        # Ask the question (with mode for article vs reviewer)
        # Use await for async LLM call - keeps event loop responsive
        result = await chat_service.ask_question(
            notebook_id=request.notebook_id,
            question=request.message,
            conversation_history=history,
            mode=request.mode
        )

        return ChatResponse(
            message=result["message"],
            context_used=result["context_used"],
            timestamp=result["timestamp"]
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Chat validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Chat service error: {e}")
        import traceback
        full_traceback = traceback.format_exc()
        logger.error(f"Full traceback: {full_traceback}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to answer question: {str(e)}"
        )
