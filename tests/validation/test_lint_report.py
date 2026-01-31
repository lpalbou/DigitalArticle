"""
Tests for lint report surfaced by ExecutionService.

These tests validate that we provide structured, deterministic static feedback
alongside execution results (even when code runs).
"""

from __future__ import annotations

from uuid import uuid4

from backend.app.services.execution_service import ExecutionService
from backend.app.models.notebook import ExecutionStatus


def test_lint_report_includes_unused_imports_warning():
    service = ExecutionService()
    notebook_id = f"lint_test_{uuid4()}"

    code = """
import pandas as pd
import numpy as np

x = 1
print(x)
"""

    result = service.execute_code(code, cell_id="lint_cell_1", notebook_id=notebook_id)

    assert result.status == ExecutionStatus.SUCCESS
    # Default behavior: safe autofix runs before execution and removes provably redundant imports.
    assert result.autofix_report is not None
    assert result.autofix_report.applied is True
    assert any(c.rule_id == "DA1101" for c in result.autofix_report.changes)

    assert result.lint_report is not None
    # After autofix, the remaining lint report should not still contain the fixed import warnings.
    assert not any(i.rule_id in ("DA1001", "DA1101") for i in result.lint_report.issues)


def test_lint_report_warns_on_possibly_undefined_names():
    service = ExecutionService()
    notebook_id = f"lint_test_{uuid4()}"

    code = """
print(definitely_missing_name_abc123)
"""

    result = service.execute_code(code, cell_id="lint_cell_2", notebook_id=notebook_id)

    assert result.status == ExecutionStatus.ERROR
    assert result.lint_report is not None

    issues = result.lint_report.issues
    assert any(i.rule_id == "DA1002" and "definitely_missing_name_abc123" in i.message for i in issues)

