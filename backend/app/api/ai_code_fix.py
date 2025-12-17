"""
API endpoints for AI-assisted code fixing.
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from ..services.llm_service import LLMService
from ..services.notebook_service import NotebookService

logger = logging.getLogger(__name__)

router = APIRouter()

class SelectedLines(BaseModel):
    """Model for selected lines context."""
    start: int
    end: int
    text: str

class AICodeFixRequest(BaseModel):
    """Request model for AI code fixing."""
    original_code: str
    current_code: str
    fix_request: str
    cell_id: str
    selected_lines: SelectedLines | None = None

class AICodeFixResponse(BaseModel):
    """Response model for AI code fixing."""
    fixed_code: str
    explanation: str
    changes_made: list[str]

@router.post("/ai-fix", response_model=AICodeFixResponse)
async def fix_code_with_ai(request: AICodeFixRequest) -> AICodeFixResponse:
    """
    Fix code using AI assistance based on user request.
    
    Args:
        request: The code fix request containing original code, current code, and fix description
        
    Returns:
        AICodeFixResponse with fixed code and explanation
        
    Raises:
        HTTPException: If the fix generation fails
    """
    try:
        logger.info(f"Processing AI code fix request for cell {request.cell_id}")
        
        # Initialize LLM service
        llm_service = LLMService()
        
        # Construct the AI prompt for code fixing
        selection_context = ""
        if request.selected_lines:
            selection_context = f"""

SELECTED LINES (Lines {request.selected_lines.start}-{request.selected_lines.end}) - USER'S FOCUS AREA:
```python
{request.selected_lines.text}
```

The user has specifically highlighted these lines, so pay special attention to this section when applying the fix.
"""

        fix_prompt = f"""You are an expert Python developer helping to fix code issues.

ORIGINAL CODE:
```python
{request.original_code}
```

CURRENT CODE (may have been modified):
```python
{request.current_code}
```{selection_context}

USER REQUEST:
{request.fix_request}

Please provide:
1. The fixed code (complete, ready to run)
2. A brief explanation of what was changed
3. A list of specific changes made

Focus on:
- Fixing syntax errors, logic errors, and runtime issues
- Improving code quality and performance when requested
- Adding proper error handling when needed
- Following Python best practices
- Maintaining the original functionality unless explicitly asked to change it
{f"- Pay special attention to lines {request.selected_lines.start}-{request.selected_lines.end} as highlighted by the user" if request.selected_lines else ""}

Respond in the following format:
FIXED_CODE:
```python
[your fixed code here]
```

EXPLANATION:
[brief explanation of changes]

CHANGES:
- [specific change 1]
- [specific change 2]
- [etc.]
"""

        # Generate the fix using LLM - Route through proper error handling system
        if not llm_service.llm:
            raise HTTPException(
                status_code=503,
                detail="LLM service is not available"
            )
        
        # Check if this is an error-fixing request (has error context)
        # If so, route through suggest_improvements for proper error analysis
        is_error_fix = any(keyword in request.fix_request.lower() for keyword in [
            'error', 'fix', 'bug', 'exception', 'traceback', 'failed', 'broken'
        ])
        
        if is_error_fix:
            # Route through ErrorAnalyzer system for proper error handling
            logger.info("🔄 Routing through ErrorAnalyzer system for error-based fix")
            try:
                # Use async suggest_improvements for non-blocking LLM call
                fixed_code, _, _ = await llm_service.asuggest_improvements(
                    prompt=f"User request: {request.fix_request}",
                    code=request.current_code,
                    error_message=f"User reported issue: {request.fix_request}",
                    error_type="UserReportedIssue",
                    traceback=""
                )

                # Create explanation and changes from the fix
                explanation = f"Applied fix based on user request: {request.fix_request}"
                changes = [
                    "Analyzed code using ErrorAnalyzer system",
                    "Applied domain-specific fixes based on error patterns",
                    f"Addressed user concern: {request.fix_request[:100]}..."
                ]

            except Exception as e:
                logger.warning(f"ErrorAnalyzer route failed, falling back to direct LLM: {e}")
                # Fallback to direct async LLM call
                response = await llm_service.llm.agenerate(
                    fix_prompt,
                    max_tokens=2000,
                    temperature=0.1
                )
                fixed_code, explanation, changes = _parse_fix_response(response.content)
        else:
            # For non-error improvements (performance, style, etc.), direct async LLM is fine
            logger.info("🎨 Using direct LLM for non-error improvement request")
            response = await llm_service.llm.agenerate(
                fix_prompt,
                max_tokens=2000,
                temperature=0.1
            )
            fixed_code, explanation, changes = _parse_fix_response(response.content)
        
        logger.info(f"Successfully generated AI code fix for cell {request.cell_id}")
        
        return AICodeFixResponse(
            fixed_code=fixed_code,
            explanation=explanation,
            changes_made=changes
        )
        
    except Exception as e:
        logger.error(f"Failed to generate AI code fix: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate code fix: {str(e)}"
        )

def _parse_fix_response(response: str) -> tuple[str, str, list[str]]:
    """
    Parse the LLM response to extract fixed code, explanation, and changes.
    
    Args:
        response: Raw LLM response
        
    Returns:
        Tuple of (fixed_code, explanation, changes_list)
    """
    try:
        # Extract fixed code
        fixed_code = ""
        if "FIXED_CODE:" in response:
            code_section = response.split("FIXED_CODE:")[1]
            if "```python" in code_section:
                code_start = code_section.find("```python") + 9
                code_end = code_section.find("```", code_start)
                if code_end != -1:
                    fixed_code = code_section[code_start:code_end].strip()
        
        # Extract explanation
        explanation = ""
        if "EXPLANATION:" in response:
            exp_section = response.split("EXPLANATION:")[1]
            if "CHANGES:" in exp_section:
                explanation = exp_section.split("CHANGES:")[0].strip()
            else:
                explanation = exp_section.strip()
        
        # Extract changes
        changes = []
        if "CHANGES:" in response:
            changes_section = response.split("CHANGES:")[1].strip()
            for line in changes_section.split('\n'):
                line = line.strip()
                if line.startswith('- '):
                    changes.append(line[2:])
                elif line and not line.startswith('#'):
                    changes.append(line)
        
        # Fallback if parsing fails
        if not fixed_code:
            # Try to extract any code block
            import re
            code_blocks = re.findall(r'```python\n(.*?)\n```', response, re.DOTALL)
            if code_blocks:
                fixed_code = code_blocks[0].strip()
            else:
                # Last resort - return the original response
                fixed_code = response.strip()
        
        if not explanation:
            explanation = "Code has been fixed based on your request."
        
        if not changes:
            changes = ["Applied requested fixes to the code"]
        
        return fixed_code, explanation, changes
        
    except Exception as e:
        logger.error(f"Failed to parse fix response: {e}")
        # Return safe defaults
        return response.strip(), "Failed to parse fix details", ["Applied fixes"]
