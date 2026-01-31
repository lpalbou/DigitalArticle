"""
Autofix models (deterministic non-LLM code rewrites).

Autofix is a trust boundary: whenever we rewrite code, we must be explicit,
auditable, and reversible.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from .linting import LintReport


class AutofixChange(BaseModel):
    """A single applied autofix change."""

    rule_id: str
    message: str
    line: Optional[int] = None


class AutofixReport(BaseModel):
    """Autofix metadata attached to an execution result."""

    enabled: bool = False
    applied: bool = False

    original_code: Optional[str] = None
    fixed_code: Optional[str] = None
    diff: Optional[str] = None

    changes: List[AutofixChange] = Field(default_factory=list)

    lint_before: Optional[LintReport] = None
    lint_after: Optional[LintReport] = None

