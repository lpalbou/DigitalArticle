"""
Linting models (static quality feedback).

These models are intentionally small and stable: they are part of the API surface
between backend execution and the frontend UI ("Execution Details" modal).
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class LintSeverity(str, Enum):
    """Severity level for lint findings."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class LintIssue(BaseModel):
    """A single lint issue detected in a cell's code."""

    severity: LintSeverity
    message: str

    # Optional machine-readable identity (e.g., DA1001 or a future Ruff rule like F401)
    rule_id: Optional[str] = None

    # 1-based line number / 0-based column offset (mirrors Python's SyntaxError shape)
    line: Optional[int] = None
    column: Optional[int] = None

    suggestion: Optional[str] = None
    fixable: bool = False


class LintReport(BaseModel):
    """Structured lint report returned alongside execution results."""

    engine: str = "builtin"
    issues: List[LintIssue] = Field(default_factory=list)

