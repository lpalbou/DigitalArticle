"""
Trace models for perfect observability (ADR 0005).

This module defines the schema for persistent, queryable traces of all LLM and agentic calls.
Traces form a hierarchy: flow → task → step.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class TraceLevel(str, Enum):
    """Hierarchy level of a trace event."""
    FLOW = "flow"      # Root-level user operation (e.g., "execute notebook")
    TASK = "task"      # Major sub-operation (e.g., "execute cell", "export PDF")
    STEP = "step"      # Atomic action (e.g., "LLM call", "code execution")


class StepType(str, Enum):
    """Type of step within a trace."""
    # LLM operations
    LLM_CODE_GENERATION = "llm_code_generation"
    LLM_CODE_FIX = "llm_code_fix"
    LLM_METHODOLOGY = "llm_methodology"
    LLM_REVIEW = "llm_review"
    LLM_CHAT = "llm_chat"
    LLM_SEMANTIC_EXTRACTION = "llm_semantic_extraction"
    LLM_ERROR_ANALYSIS = "llm_error_analysis"
    LLM_LOGIC_VALIDATION = "llm_logic_validation"  # ADR 0004: semantic correctness check
    LLM_LOGIC_CORRECTION = "llm_logic_correction"  # ADR 0004: fix after validation failure
    
    # Execution operations
    CODE_EXECUTION = "code_execution"
    CODE_LINT = "code_lint"
    CODE_AUTOFIX = "code_autofix"
    
    # Other operations
    FILE_UPLOAD = "file_upload"
    FILE_PREVIEW = "file_preview"
    EXPORT_PDF = "export_pdf"
    EXPORT_SEMANTIC = "export_semantic"
    MODEL_DOWNLOAD = "model_download"
    
    # Meta
    RETRY = "retry"
    LOGIC_CORRECTION = "logic_correction"  # For 0009: post-success validation


class TraceStatus(str, Enum):
    """Status of a trace event."""
    STARTED = "started"
    SUCCESS = "success"
    ERROR = "error"
    CANCELLED = "cancelled"


class TraceEvent(BaseModel):
    """
    A single trace event in the observability system.
    
    Hierarchy:
    - flow_id: Root operation (user action like "execute cell")
    - task_id: Sub-operation within flow
    - step_id: This specific event
    - parent_step_id: Parent event for nested steps
    """
    # Identity
    step_id: str = Field(default_factory=lambda: str(uuid4()))
    flow_id: str
    task_id: Optional[str] = None
    parent_step_id: Optional[str] = None
    
    # Classification
    level: TraceLevel
    step_type: StepType
    status: TraceStatus = TraceStatus.STARTED
    
    # Timing
    started_at: datetime = Field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    
    # Context (what triggered this)
    notebook_id: Optional[str] = None
    cell_id: Optional[str] = None
    user_id: Optional[str] = None  # For future multi-user support
    
    # LLM-specific (when step_type is LLM_*)
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    llm_prompt: Optional[str] = None           # User/task prompt (may be truncated for storage)
    llm_system_prompt: Optional[str] = None    # System prompt (may be truncated)
    llm_response: Optional[str] = None         # LLM response content (may be truncated)
    llm_input_tokens: Optional[int] = None
    llm_output_tokens: Optional[int] = None
    llm_total_tokens: Optional[int] = None
    llm_generation_time_ms: Optional[float] = None
    llm_temperature: Optional[float] = None
    llm_seed: Optional[int] = None
    
    # Execution-specific (when step_type is CODE_*)
    exec_code: Optional[str] = None
    exec_stdout: Optional[str] = None
    exec_stderr: Optional[str] = None
    exec_error: Optional[str] = None
    exec_error_type: Optional[str] = None
    
    # Generic payload for extensibility
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Error details (when status is ERROR)
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    
    class Config:
        use_enum_values = True


def redact_secrets(text: Optional[str]) -> Optional[str]:
    """
    Redact potential secrets from trace data.
    
    Patterns:
    - API keys (sk-*, key-*, api_key=*, etc.)
    - Bearer tokens
    - Base64-encoded credentials
    """
    if not text:
        return text
    
    import re
    
    # Redact common API key patterns
    patterns = [
        (r'(sk-[a-zA-Z0-9_-]{20,})', '[REDACTED_API_KEY]'),
        (r'(key-[a-zA-Z0-9_-]{20,})', '[REDACTED_API_KEY]'),
        (r'(api[_-]?key["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_-]{20,})', r'\1[REDACTED]'),
        (r'(Bearer\s+)([a-zA-Z0-9_.-]{20,})', r'\1[REDACTED_TOKEN]'),
        (r'(password["\']?\s*[:=]\s*["\']?)([^\s"\']+)', r'\1[REDACTED]'),
        (r'(secret["\']?\s*[:=]\s*["\']?)([^\s"\']+)', r'\1[REDACTED]'),
    ]
    
    result = text
    for pattern, replacement in patterns:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    
    return result


def truncate_for_storage(text: Optional[str], max_length: int = 10000, notice: bool = True) -> Optional[str]:
    """
    Truncate text for storage while preserving start and end.
    
    Per ADR 0003: truncation must be explicit and logged.
    """
    if not text or len(text) <= max_length:
        return text
    
    # Keep first 60% and last 30%, with 10% for notice
    head_len = int(max_length * 0.6)
    tail_len = int(max_length * 0.3)
    
    if notice:
        truncation_notice = f"\n\n#TRUNCATION_NOTICE: {len(text) - max_length} chars omitted for storage\n\n"
    else:
        truncation_notice = "\n...[truncated]...\n"
    
    return text[:head_len] + truncation_notice + text[-tail_len:]
