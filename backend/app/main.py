"""
FastAPI main application for the Digital Article.

This application provides a REST API for managing notebook cells, executing Python code,
and integrating with LLM services for prompt-to-code conversion.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import traceback
import logging
import os
from pathlib import Path

from .api import cells, notebooks, llm, files

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Digital Article API",
    description="API for managing analytics notebooks with natural language prompts",
    version="1.0.0"
)

# Global exception handler to show FULL Python execution errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Capture ALL errors and show complete stack traces."""
    
    full_traceback = traceback.format_exc()
    
    logger.error(f"🚨 EXECUTION ERROR in {request.method} {request.url}")
    logger.error(f"🚨 Exception: {exc}")
    logger.error(f"🚨 FULL STACK TRACE:\n{full_traceback}")
    
    error_response = {
        "detail": f"EXECUTION ERROR:\n\n{type(exc).__name__}: {str(exc)}\n\nFULL STACK TRACE:\n{full_traceback}",
        "error_type": type(exc).__name__,
        "error_message": str(exc),
        "stack_trace": full_traceback,
        "request_url": str(request.url),
        "request_method": request.method
    }
    
    return JSONResponse(
        status_code=500,
        content=error_response
    )

# Configure CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(cells.router, prefix="/api/cells", tags=["cells"])
app.include_router(notebooks.router, prefix="/api/notebooks", tags=["notebooks"])
app.include_router(llm.router, prefix="/api/llm", tags=["llm"])
app.include_router(files.router, prefix="/api/files", tags=["files"])

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Digital Article API", "status": "running"}

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
