from backend.app.services.logic_issue_selection import LogicIssueSelector
from backend.app.services.logic_validation_service import (
    CategorizedIssue,
    IssueSeverity,
    LogicValidationReport,
    LogicValidationResult,
)


def test_high_trigger_includes_evidence_backed_medium_issues() -> None:
    selector = LogicIssueSelector(max_extra_medium_with_high=3)

    report = LogicValidationReport(
        result=LogicValidationResult.FAIL,
        issues=[],
        suggestions=[],
        categorized_issues=[
            CategorizedIssue(
                issue="HIGH issue",
                severity=IssueSeverity.HIGH,
                evidence_code="some_code_snippet",
            ),
            CategorizedIssue(
                issue="MEDIUM issue with evidence",
                severity=IssueSeverity.MEDIUM,
                evidence_output="some_stdout_snippet",
            ),
            CategorizedIssue(
                issue="MEDIUM issue without evidence should not be included",
                severity=IssueSeverity.MEDIUM,
                evidence_code=None,
                evidence_output=None,
            ),
        ],
    )

    selection = selector.select(report)

    assert selection.severity_to_fix == IssueSeverity.HIGH
    issues = [ci.issue for ci in selection.issues_to_fix]
    assert "HIGH issue" in issues
    assert "MEDIUM issue with evidence" in issues
    assert "MEDIUM issue without evidence should not be included" not in issues


def test_no_high_selects_medium_only() -> None:
    selector = LogicIssueSelector()

    report = LogicValidationReport(
        result=LogicValidationResult.FAIL,
        issues=[],
        suggestions=[],
        categorized_issues=[
            CategorizedIssue(
                issue="MEDIUM issue",
                severity=IssueSeverity.MEDIUM,
                evidence_code="e",
            )
        ],
    )

    selection = selector.select(report)
    assert selection.severity_to_fix == IssueSeverity.MEDIUM
    assert [ci.issue for ci in selection.issues_to_fix] == ["MEDIUM issue"]

