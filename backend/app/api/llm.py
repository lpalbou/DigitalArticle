"""
API endpoints for LLM operations.

This module provides REST endpoints for LLM-related functionality
such as code generation and explanation.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from ..services.shared import notebook_service

router = APIRouter()

# Get LLM service from shared notebook service
llm_service = notebook_service.llm_service


class CodeGenerationRequest(BaseModel):
    """Request model for code generation."""
    prompt: str
    context: dict = {}


class CodeExplanationRequest(BaseModel):
    """Request model for code explanation."""
    code: str


class CodeImprovementRequest(BaseModel):
    """Request model for code improvement."""
    prompt: str
    code: str
    error_message: str = None


@router.post("/generate-code")
async def generate_code(request: CodeGenerationRequest):
    """Generate Python code from a natural language prompt."""
    try:
        code = llm_service.generate_code_from_prompt(
            request.prompt, 
            request.context if request.context else None
        )
        return {"code": code}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate code: {str(e)}"
        )


@router.post("/explain-code")
async def explain_code(request: CodeExplanationRequest):
    """Generate a natural language explanation of Python code."""
    try:
        explanation = llm_service.explain_code(request.code)
        return {"explanation": explanation}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to explain code: {str(e)}"
        )


@router.post("/improve-code")
async def improve_code(request: CodeImprovementRequest):
    """Suggest improvements or fixes for Python code."""
    try:
        improved_code = llm_service.suggest_improvements(
            request.prompt,
            request.code,
            request.error_message
        )
        return {"improved_code": improved_code}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to improve code: {str(e)}"
        )


@router.get("/status")
async def get_llm_status():
    """Get the status of the LLM service."""
    try:
        return {
            "provider": llm_service.provider,
            "model": llm_service.model,
            "status": "ready" if llm_service.llm else "not_initialized"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get LLM status: {str(e)}"
        )
