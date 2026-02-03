"""
Logic issue selection for correction (ADR 0004).

Why this exists
---------------
We run Logic Validation after a successful execution. When validation FAILs, we decide what to
ask the model to correct.

The naive approach ("only fix the highest severity bucket") can lead to wasted correction calls:
- A spurious HIGH issue can trigger a correction attempt that doesn't address the real problem.
- MEDIUM issues that are explicitly grounded in code/output (with evidence) are often cheap to fix
  and should be included when we are *already* spending a correction call.

This selector keeps the behavior explicit and testable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from .logic_validation_service import CategorizedIssue, IssueSeverity, LogicValidationReport


@dataclass(frozen=True)
class IssueSelection:
    """Output of the selection step."""

    severity_to_fix: Optional[IssueSeverity]
    issues_to_fix: List[CategorizedIssue]


class LogicIssueSelector:
    """
    Selects which issues should be passed into the logic correction prompt.

    Policy (general-purpose):
    - Choose the highest severity bucket that exists.
    - If a HIGH correction is triggered, also include a small number of evidence-backed MEDIUM issues.
      Rationale: we are already spending an LLM correction call; adding the most grounded medium issues
      often resolves the real user-visible mismatch in one shot, without needing a second correction loop.
    """

    def __init__(self, *, max_extra_medium_with_high: int = 3):
        self._max_extra_medium_with_high = max(0, int(max_extra_medium_with_high))

    def select(self, report: LogicValidationReport) -> IssueSelection:
        high = report.get_issues_by_severity(IssueSeverity.HIGH)
        medium = report.get_issues_by_severity(IssueSeverity.MEDIUM)
        low = report.get_issues_by_severity(IssueSeverity.LOW)

        if high:
            selected: List[CategorizedIssue] = list(high)
            if self._max_extra_medium_with_high > 0 and medium:
                extra = [ci for ci in medium if _has_verifiable_evidence(ci)]
                selected.extend(extra[: self._max_extra_medium_with_high])
            return IssueSelection(severity_to_fix=IssueSeverity.HIGH, issues_to_fix=selected)

        if medium:
            return IssueSelection(severity_to_fix=IssueSeverity.MEDIUM, issues_to_fix=list(medium))

        if low:
            return IssueSelection(severity_to_fix=IssueSeverity.LOW, issues_to_fix=list(low))

        return IssueSelection(severity_to_fix=None, issues_to_fix=[])


def _has_verifiable_evidence(ci: CategorizedIssue) -> bool:
    """
    Evidence presence heuristic.

    We treat evidence as present if the validator provided a non-empty snippet that is not the literal "NONE".
    """

    for ev in (ci.evidence_code, ci.evidence_output):
        if not ev:
            continue
        if ev.strip().upper() == "NONE":
            continue
        return True
    return False

