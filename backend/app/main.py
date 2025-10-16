"""
FastAPI main application for the Reverse Analytics Notebook.

This application provides a REST API for managing notebook cells, executing Python code,
and integrating with LLM services for prompt-to-code conversion.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from pathlib import Path

from .api import cells, notebooks, llm

app = FastAPI(
    title="Reverse Analytics Notebook API",
    description="API for managing analytics notebooks with natural language prompts",
    version="1.0.0"
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

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Reverse Analytics Notebook API", "status": "running"}

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
