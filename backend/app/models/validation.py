"""
Validation Models for Digital Article

Defines data models for the two-path validation system:
- Path 1: Execution Validation (technical correctness - code runs)
- Path 2: Logical Validation (semantic correctness - code makes sense)

This module provides a clean, typed interface for validators to report their findings
and for the notebook service to orchestrate retry logic based on validation results.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ValidationPhase(str, Enum):
    """Validation phase identifier."""
    EXECUTION = "execution"  # Technical - code runs without Python errors
    LOGICAL = "logical"      # Semantic - code produces valid/meaningful results


class ValidationSeverity(str, Enum):
    """Severity level for validation findings."""
    INFO = "info"          # Informational only, no action needed
    WARNING = "warning"    # Should review, but may proceed
    ERROR = "error"        # Must fix, triggers retry
    CRITICAL = "critical"  # Fundamental issue, definitely retry


class ValidationResult(BaseModel):
    """
    Result from a single validator.

    Represents the outcome of checking one specific validation rule
    (e.g., "parameters at bounds", "circular reasoning", etc.).
    """

    validator_name: str = Field(..., description="Name of the validator that produced this result")
    phase: ValidationPhase = Field(..., description="Which validation phase this belongs to")
    passed: bool = Field(..., description="True if validation passed, False if failed")
    severity: ValidationSeverity = Field(
        default=ValidationSeverity.INFO,
        description="Severity level of the finding (if failed)"
    )
    message: str = Field(..., description="Human-readable message describing the finding")
    details: Optional[str] = Field(
        default=None,
        description="Additional details or context about the finding"
    )
    suggestion: Optional[str] = Field(
        default=None,
        description="Suggested fix or action for the user/LLM"
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional context data for LLM retry (e.g., available columns, expected ranges)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "validator_name": "statistical_validity.parameter_at_bounds",
                "phase": "logical",
                "passed": False,
                "severity": "error",
                "message": "Parameter(s) at optimizer bounds - results unreliable",
                "suggestion": "Try different initial values or simplify model"
            }
        }


class ValidationReport(BaseModel):
    """
    Aggregated results from all validators in a phase.

    This is returned after running all validators for a specific phase
    (execution or logical) and determines whether retry is needed.
    """

    phase: ValidationPhase = Field(..., description="Which validation phase this report is for")
    passed: bool = Field(
        ...,
        description="True if all validators passed or only had warnings/info"
    )
    should_retry: bool = Field(
        ...,
        description="True if any ERROR or CRITICAL findings require retry"
    )
    results: List[ValidationResult] = Field(
        default_factory=list,
        description="Individual validation results from all validators"
    )

    def get_llm_guidance(self) -> str:
        """
        Format validation failures as guidance for LLM retry.

        Extracts all ERROR and CRITICAL findings and formats them as
        a clear, actionable message for the LLM to use when regenerating code.

        Returns:
            Formatted string with validation failures and suggestions
        """
        guidance_lines = []

        for result in self.results:
            if not result.passed and result.severity in (
                ValidationSeverity.ERROR,
                ValidationSeverity.CRITICAL
            ):
                guidance_lines.append(f"[{result.validator_name}] {result.message}")
                if result.suggestion:
                    guidance_lines.append(f"  Suggestion: {result.suggestion}")
                if result.details:
                    guidance_lines.append(f"  Details: {result.details}")
                guidance_lines.append("")  # Blank line for readability

        return "\n".join(guidance_lines)

    def get_warnings(self) -> List[str]:
        """
        Extract all WARNING level findings.

        Returns:
            List of warning messages (passive, no retry triggered)
        """
        return [
            result.message
            for result in self.results
            if not result.passed and result.severity == ValidationSeverity.WARNING
        ]

    def has_errors(self) -> bool:
        """Check if any ERROR or CRITICAL findings exist."""
        return any(
            not r.passed and r.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL)
            for r in self.results
        )

    def summary(self) -> str:
        """Get a human-readable summary of the validation report."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed

        if failed == 0:
            return f"✅ All {total} validations passed"

        errors = sum(
            1 for r in self.results
            if not r.passed and r.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL)
        )
        warnings = sum(
            1 for r in self.results
            if not r.passed and r.severity == ValidationSeverity.WARNING
        )

        parts = []
        if errors > 0:
            parts.append(f"{errors} error(s)")
        if warnings > 0:
            parts.append(f"{warnings} warning(s)")

        return f"⚠️ Validation found {', '.join(parts)} ({passed}/{total} checks passed)"

    class Config:
        json_schema_extra = {
            "example": {
                "phase": "logical",
                "passed": False,
                "should_retry": True,
                "results": [
                    {
                        "validator_name": "statistical_validity.coefficient_of_variation",
                        "phase": "logical",
                        "passed": False,
                        "severity": "error",
                        "message": "Poor parameter precision (%CV > 100%)",
                        "suggestion": "Model may be overparameterized or data insufficient"
                    }
                ]
            }
        }
