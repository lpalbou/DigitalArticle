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
from pydantic import BaseModel, Field, field_validator, model_validator

from ..config import DEFAULT_LLM_PROVIDER, DEFAULT_LLM_MODEL
from .linting import LintReport
from .autofix import AutofixReport


def sanitize_for_json(obj: Any) -> Any:
    """
    Recursively convert numpy/pandas types to JSON-serializable Python types.
    
    This handles:
    - numpy.dtypes.* classes (new in NumPy 2.x / Pandas 2.x)
    - np.dtype instances
    - np.ndarray
    - np.integer, np.floating, np.generic
    - Nested dicts and lists
    
    Args:
        obj: Any object to sanitize
        
    Returns:
        JSON-serializable version of the object
    """
    import pandas as pd
    
    # Handle None
    if obj is None:
        return None
    
    # Handle numpy dtype objects (including new numpy.dtypes.* types)
    # Check for dtype attribute and name pattern - covers both old and new numpy dtype systems
    if hasattr(obj, 'name') and hasattr(obj, 'kind') and hasattr(obj, 'itemsize'):
        # This is a dtype object (old np.dtype or new numpy.dtypes.*)
        return str(obj)
    
    # Also check if it's a dtype class/type itself (rare edge case)
    if isinstance(obj, type) and 'dtype' in str(obj).lower():
        return str(obj)
    
    # Handle np.dtype explicitly (catches instances)
    if isinstance(obj, np.dtype):
        return str(obj)
    
    # Handle pandas NaT and NaN
    try:
        if pd.isna(obj):
            return None
    except (TypeError, ValueError):
        pass
    
    # Handle pandas Timestamp
    if hasattr(pd, 'Timestamp') and isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    
    # Handle pandas Period
    if hasattr(pd, 'Period') and isinstance(obj, pd.Period):
        return str(obj)
    
    # Handle numpy scalar types
    if isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    
    if isinstance(obj, np.bool_):
        return bool(obj)
    
    if isinstance(obj, np.generic):
        return obj.item()
    
    # Handle numpy arrays
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    
    # Handle datetime
    if isinstance(obj, datetime):
        return obj.isoformat()
    
    # Handle UUID
    if isinstance(obj, UUID):
        return str(obj)
    
    # Handle dicts recursively
    if isinstance(obj, dict):
        return {sanitize_for_json(k): sanitize_for_json(v) for k, v in obj.items()}
    
    # Handle lists and tuples recursively
    if isinstance(obj, (list, tuple)):
        return [sanitize_for_json(item) for item in obj]
    
    # Handle sets
    if isinstance(obj, set):
        return [sanitize_for_json(item) for item in obj]
    
    # Return as-is for basic types (str, int, float, bool)
    return obj


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


class CellState(str, Enum):
    """State of cell content freshness."""
    FRESH = "fresh"          # Recently executed, results are current
    STALE = "stale"          # May be outdated due to upstream changes
    EXECUTING = "executing"  # Currently running


class ExecutionResult(BaseModel):
    """Result of executing a cell."""
    
    status: ExecutionStatus = ExecutionStatus.PENDING
    stdout: str = ""
    stderr: str = ""
    execution_time: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Rich output data
    plots: List[Union[str, Dict[str, Any]]] = Field(default_factory=list)  # Base64 strings or plot dicts with labels
    tables: List[Dict[str, Any]] = Field(default_factory=list)  # Structured table data
    images: List[str] = Field(default_factory=list)  # Base64 encoded images
    interactive_plots: List[Dict[str, Any]] = Field(default_factory=list)  # Plotly JSON data
    
    # Error information
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    traceback: Optional[str] = None

    # Statistical and validation warnings (non-fatal issues)
    warnings: List[str] = Field(default_factory=list)

    # Static quality feedback (linting) to help users/LLM improve code even when it runs
    lint_report: Optional[LintReport] = None

    # Deterministic safe code rewrites (default-on; strict allowlist)
    autofix_report: Optional[AutofixReport] = None
    
    @model_validator(mode='before')
    @classmethod
    def sanitize_inputs(cls, data: Any) -> Any:
        """Sanitize all inputs BEFORE validation to handle numpy/pandas types."""
        if isinstance(data, dict):
            return sanitize_for_json(data)
        return data


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
    cell_state: CellState = CellState.FRESH  # Content freshness state
    
    # Generation metadata (AbstractCore 2.5.2+)
    last_generation_time_ms: Optional[float] = None  # Generation time in milliseconds
    last_execution_timestamp: Optional[datetime] = None  # When the cell was last executed
    
    # Display preferences
    show_code: bool = False  # Toggle between prompt and code view
    
    # Metadata
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # LLM Execution Traces (persistent storage of all LLM interactions)
    llm_traces: List[Dict[str, Any]] = Field(default_factory=list)
    
    @model_validator(mode='before')
    @classmethod
    def sanitize_inputs(cls, data: Any) -> Any:
        """Sanitize all inputs BEFORE validation to handle numpy/pandas types."""
        if isinstance(data, dict):
            return sanitize_for_json(data)
        return data


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
    llm_model: str = DEFAULT_LLM_MODEL
    llm_provider: str = DEFAULT_LLM_PROVIDER
    custom_seed: Optional[int] = None  # User-defined seed for reproducibility

    # Token tracking
    last_context_tokens: int = 0  # Last known context size from generation
    
    # Abstract
    abstract: str = ""  # Generated scientific abstract
    abstract_generated_at: Optional[datetime] = None  # When abstract was last generated

    @model_validator(mode='before')
    @classmethod
    def sanitize_inputs(cls, data: Any) -> Any:
        """Sanitize all inputs BEFORE validation to handle numpy/pandas types."""
        if isinstance(data, dict):
            return sanitize_for_json(data)
        return data
    
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
    autofix: bool = True  # Default: safe deterministic autofix before execution
    clean_rerun: bool = False  # If True, rebuild execution context from upstream cells only (ignore downstream state)


class CellExecuteResponse(BaseModel):
    """Response model for cell execution containing both the updated cell and execution result."""
    cell: 'Cell'
    result: ExecutionResult
    
    @model_validator(mode='before')
    @classmethod
    def sanitize_inputs(cls, data: Any) -> Any:
        """Sanitize all inputs BEFORE validation to handle numpy/pandas types."""
        if isinstance(data, dict):
            return sanitize_for_json(data)
        return data


class NotebookCreateRequest(BaseModel):
    """Request model for creating a new notebook."""
    title: str = "Untitled Digital Article"
    description: str = ""
    author: str = ""
    llm_model: str = DEFAULT_LLM_MODEL
    llm_provider: str = DEFAULT_LLM_PROVIDER


class NotebookUpdateRequest(BaseModel):
    """Request model for updating a notebook."""
    title: Optional[str] = None
    description: Optional[str] = None
    author: Optional[str] = None
    tags: Optional[List[str]] = None
    llm_model: Optional[str] = None
    llm_provider: Optional[str] = None
    custom_seed: Optional[int] = None
