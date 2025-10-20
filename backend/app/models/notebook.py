"""
Data models for the Digital Article.

These Pydantic models define the core data structures for notebooks, cells, and execution results.
They ensure type safety and provide serialization/deserialization capabilities.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from uuid import UUID, uuid4

import numpy as np
from pydantic import BaseModel, Field


class CellType(str, Enum):
    """Types of cells in a notebook."""
    PROMPT = "prompt"  # Natural language prompt cells
    CODE = "code"      # Raw code cells (for advanced users)
    MARKDOWN = "markdown"  # Documentation cells
    METHODOLOGY = "methodology"  # Scientific methodology explanations


class ExecutionStatus(str, Enum):
    """Status of cell execution."""
    PENDING = "pending"      # Not yet executed
    RUNNING = "running"      # Currently executing
    SUCCESS = "success"      # Executed successfully
    ERROR = "error"         # Execution failed
    CANCELLED = "cancelled"  # Execution was cancelled


class ExecutionResult(BaseModel):
    """Result of executing a cell."""
    
    status: ExecutionStatus = ExecutionStatus.PENDING
    stdout: str = ""
    stderr: str = ""
    execution_time: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Rich output data
    plots: List[str] = Field(default_factory=list)  # Base64 encoded plot images
    tables: List[Dict[str, Any]] = Field(default_factory=list)  # Structured table data
    images: List[str] = Field(default_factory=list)  # Base64 encoded images
    interactive_plots: List[Dict[str, Any]] = Field(default_factory=list)  # Plotly JSON data
    
    # Error information
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    traceback: Optional[str] = None
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            np.dtype: lambda v: str(v),
            np.generic: lambda v: v.item(),
            np.ndarray: lambda v: v.tolist()
        }


class Cell(BaseModel):
    """A single cell in a notebook."""
    
    id: UUID = Field(default_factory=uuid4)
    cell_type: CellType = CellType.PROMPT
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # Content
    prompt: str = ""  # Natural language prompt
    code: str = ""    # Generated or manually written Python code
    markdown: str = ""  # Markdown content for documentation cells
    scientific_explanation: str = ""  # AI-generated scientific article-style explanation
    
    # Execution state
    execution_count: int = 0
    last_result: Optional[ExecutionResult] = None
    is_executing: bool = False
    is_writing_methodology: bool = False
    is_retrying: bool = False  # Track if auto-retry is in progress
    retry_count: int = 0  # Number of retry attempts
    
    # Display preferences
    show_code: bool = False  # Toggle between prompt and code view
    
    # Metadata
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
            np.dtype: lambda v: str(v),
            np.generic: lambda v: v.item(),
            np.ndarray: lambda v: v.tolist()
        }


class Notebook(BaseModel):
    """A complete notebook containing multiple cells."""
    
    id: UUID = Field(default_factory=uuid4)
    title: str = "Untitled Digital Article"
    description: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # Cells
    cells: List[Cell] = Field(default_factory=list)
    
    # Metadata
    author: str = ""
    version: str = "1.0.0"
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Configuration
    llm_model: str = "qwen/qwen3-next-80b"
    llm_provider: str = "lmstudio"
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
            np.dtype: lambda v: str(v),
            np.generic: lambda v: v.item(),
            np.ndarray: lambda v: v.tolist()
        }
    
    def add_cell(self, cell_type: CellType = CellType.PROMPT, content: str = "") -> Cell:
        """Add a new cell to the notebook."""
        cell = Cell(cell_type=cell_type)
        
        if cell_type == CellType.PROMPT:
            cell.prompt = content
        elif cell_type == CellType.CODE:
            cell.code = content
        elif cell_type == CellType.MARKDOWN:
            cell.markdown = content
            
        self.cells.append(cell)
        self.updated_at = datetime.now()
        return cell
    
    def remove_cell(self, cell_id: UUID) -> bool:
        """Remove a cell from the notebook."""
        for i, cell in enumerate(self.cells):
            if cell.id == cell_id:
                self.cells.pop(i)
                self.updated_at = datetime.now()
                return True
        return False
    
    def get_cell(self, cell_id: UUID) -> Optional[Cell]:
        """Get a cell by ID."""
        for cell in self.cells:
            if cell.id == cell_id:
                return cell
        return None
    
    def reorder_cells(self, cell_ids: List[UUID]) -> bool:
        """Reorder cells based on provided cell IDs."""
        if len(cell_ids) != len(self.cells):
            return False
            
        cell_dict = {cell.id: cell for cell in self.cells}
        new_cells = []
        
        for cell_id in cell_ids:
            if cell_id in cell_dict:
                new_cells.append(cell_dict[cell_id])
            else:
                return False
                
        self.cells = new_cells
        self.updated_at = datetime.now()
        return True


# Request/Response models for API endpoints

class CellCreateRequest(BaseModel):
    """Request model for creating a new cell."""
    cell_type: CellType = CellType.PROMPT
    content: str = ""
    notebook_id: UUID


class CellUpdateRequest(BaseModel):
    """Request model for updating a cell."""
    prompt: Optional[str] = None
    code: Optional[str] = None
    markdown: Optional[str] = None
    show_code: Optional[bool] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    cell_type: Optional[CellType] = None


class CellExecuteRequest(BaseModel):
    """Request model for executing a cell."""
    cell_id: UUID
    notebook_id: Optional[UUID] = None  # Notebook ID for context
    force_regenerate: bool = False  # Force LLM to regenerate code even if it exists
    code: Optional[str] = None  # Direct code to execute (overrides stored code)
    prompt: Optional[str] = None  # Prompt to generate code from


class CellExecuteResponse(BaseModel):
    """Response model for cell execution containing both the updated cell and execution result."""
    cell: 'Cell'
    result: ExecutionResult


class NotebookCreateRequest(BaseModel):
    """Request model for creating a new notebook."""
    title: str = "Untitled Digital Article"
    description: str = ""
    author: str = ""
    llm_model: str = "qwen/qwen3-next-80b"
    llm_provider: str = "lmstudio"


class NotebookUpdateRequest(BaseModel):
    """Request model for updating a notebook."""
    title: Optional[str] = None
    description: Optional[str] = None
    author: Optional[str] = None
    tags: Optional[List[str]] = None
    llm_model: Optional[str] = None
    llm_provider: Optional[str] = None
