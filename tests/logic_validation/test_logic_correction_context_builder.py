from __future__ import annotations

from backend.app.models.notebook import ExecutionResult, ExecutionStatus
from backend.app.services.logic_correction_context_builder import (
    LogicCorrectionContextBuilder,
    LogicCorrectionInputs,
)
from backend.app.services.logic_validation_service import CategorizedIssue, IssueSeverity


def test_logic_correction_builder_includes_evidence_and_compacts_stdout() -> None:
    builder = LogicCorrectionContextBuilder()

    long_stdout = "A" * (builder.MAX_STDOUT_CHARS + 500)
    result = ExecutionResult(
        status=ExecutionStatus.SUCCESS,
        stdout=long_stdout,
        tables=[
            {
                "source": "display",
                "label": "Table 1: Demo",
                "shape": [2, 2],
                "columns": ["a", "b"],
                "data": [{"a": 1, "b": 2}, {"a": 3, "b": 4}],
            }
        ],
        plots=[],
        interactive_plots=[],
        images=[],
    )

    issues = [
        CategorizedIssue(
            issue="Primary result not displayed",
            severity=IssueSeverity.HIGH,
            suggestion="Add display(df, 'Table 1: ...')",
            evidence_code="print(df.head())",
            evidence_output="NONE",
        )
    ]

    text = builder.build_rerun_comment(
        LogicCorrectionInputs(
            notebook_title="My Notebook",
            notebook_description="A demo analysis",
            user_prompt="Show the top rows",
            previous_cells_brief="- (prompt ✓) Load data\n",
            issues_to_fix=issues,
            severity_label="high",
            attempt_number=1,
            execution_result=result,
            persona_combination=None,
            bibliography=None,
        )
    )

    assert "ISSUES TO FIX" in text
    assert "evidence_code:" in text
    assert "`print(df.head())`" in text
    assert "EXECUTION ARTIFACTS" in text
    assert "#COMPACTION_NOTICE: STDOUT compacted for logic correction" in text
    assert "TABLES SUMMARY" in text
    assert "Table 1: Demo" in text

