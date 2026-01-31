"""
Tests for deterministic safe autofix during execution.

Autofix is default-on (for a strict allowlist) and must be transparent
when rewrites are applied: we assert that diffs and metadata are present.
"""

from __future__ import annotations

from uuid import uuid4

from backend.app.services.execution_service import ExecutionService
from backend.app.models.notebook import ExecutionStatus


def test_autofix_removes_unused_single_import_and_emits_diff():
    service = ExecutionService()
    notebook_id = f"autofix_test_{uuid4()}"

    code = "import numpy as np\nx = 1\nprint(x)\n"

    result = service.execute_code(code, cell_id="autofix_cell_1", notebook_id=notebook_id, autofix=True)

    assert result.status == ExecutionStatus.SUCCESS
    assert result.autofix_report is not None
    assert result.autofix_report.enabled is True
    assert result.autofix_report.applied is True
    assert result.autofix_report.original_code == code
    assert result.autofix_report.fixed_code is not None
    assert "import numpy as np" not in result.autofix_report.fixed_code
    assert result.autofix_report.diff and "import numpy as np" in result.autofix_report.diff


def test_autofix_does_not_modify_multi_import_statements():
    service = ExecutionService()
    notebook_id = f"autofix_test_{uuid4()}"

    code = "import numpy as np, pandas as pd\nx = 1\nprint(x)\n"

    result = service.execute_code(code, cell_id="autofix_cell_2", notebook_id=notebook_id, autofix=True)

    assert result.status == ExecutionStatus.SUCCESS
    # Conservative engine must refuse to rewrite multi-import lines.
    # We only attach an autofix report when an actual rewrite occurs.
    assert result.autofix_report is None

