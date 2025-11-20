"""
Data models for analysis critique and post-execution evaluation.

These models represent the structured output of critiquing a completed analysis,
checking for plausibility, assumption violations, and interpretation quality.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class CritiqueSeverity(str, Enum):
    """Severity levels for critique findings."""
    CRITICAL = "critical"      # Results likely invalid
    MAJOR = "major"            # Significant concern about validity
    MINOR = "minor"            # Minor issue but analysis still useful
    INFORMATIONAL = "informational"  # FYI, not a problem


class CritiqueCategory(str, Enum):
    """Categories of critique findings."""
    RESULT_PLAUSIBILITY = "result_plausibility"
    ASSUMPTION_VIOLATION = "assumption_violation"
    INTERPRETATION_ERROR = "interpretation_error"
    METHODOLOGICAL_ISSUE = "methodological_issue"
    DATA_QUALITY = "data_quality"
    MISSING_ANALYSIS = "missing_analysis"


class CritiqueFinding(BaseModel):
    """A specific issue or observation from the critique."""
    severity: CritiqueSeverity
    category: CritiqueCategory
    title: str = Field(..., description="Short title of the finding")
    description: str = Field(..., description="Detailed description of what was found")
    impact: str = Field(..., description="How this affects interpretation/validity")
    suggestion: str = Field(..., description="How to address or mitigate this issue")
    affected_results: List[str] = Field(
        default_factory=list,
        description="Which results/outputs are affected"
    )


class PlausibilityCheck(BaseModel):
    """Result of checking whether analysis results are plausible."""
    check_name: str
    passed: bool
    details: str
    expected_range: Optional[str] = None
    actual_value: Optional[str] = None


class AssumptionCheck(BaseModel):
    """Result of checking whether method assumptions were met."""
    assumption: str
    checked: bool
    met: Optional[bool] = None  # None if not checked
    evidence: str
    consequences: str  # What happens if assumption violated


class AnalysisCritique(BaseModel):
    """
    Comprehensive critique of a completed analysis.

    This represents critical evaluation of:
    - Whether results are plausible
    - Whether assumptions were checked and met
    - Whether interpretation is appropriate
    - What's missing or could be improved
    """

    # Overall assessment
    overall_quality: str = Field(
        ...,
        description="Overall quality rating: excellent, good, fair, poor, invalid"
    )
    confidence_in_results: str = Field(
        ...,
        description="Confidence in results: high, medium, low, none"
    )
    summary: str = Field(..., description="Brief summary of critique")

    # Detailed findings
    findings: List[CritiqueFinding] = Field(
        default_factory=list,
        description="Specific issues or observations"
    )

    # Plausibility checks
    plausibility_checks: List[PlausibilityCheck] = Field(
        default_factory=list,
        description="Results of plausibility checking"
    )

    # Assumption checks
    assumption_checks: List[AssumptionCheck] = Field(
        default_factory=list,
        description="Results of checking method assumptions"
    )

    # Interpretation quality
    interpretation_strengths: List[str] = Field(
        default_factory=list,
        description="What was done well in interpretation"
    )
    interpretation_weaknesses: List[str] = Field(
        default_factory=list,
        description="Issues with interpretation or presentation"
    )

    # Recommendations
    recommended_improvements: List[str] = Field(
        default_factory=list,
        description="How to improve this analysis"
    )
    recommended_additional_analyses: List[str] = Field(
        default_factory=list,
        description="Additional analyses that would strengthen conclusions"
    )
    recommended_sensitivity_checks: List[str] = Field(
        default_factory=list,
        description="Sensitivity analyses to test robustness"
    )

    # Limitations
    identified_limitations: List[str] = Field(
        default_factory=list,
        description="Limitations that should be acknowledged"
    )

    # Alternative explanations
    alternative_explanations: List[str] = Field(
        default_factory=list,
        description="Alternative explanations for the results"
    )

    # Metadata
    critique_method: str = Field(
        default="llm_judge",
        description="How critique was performed: llm_judge, rule_based, hybrid"
    )
    llm_assessment_score: Optional[float] = Field(
        None,
        description="Numerical score from LLM-as-a-judge assessment (0-1)"
    )

    def has_critical_findings(self) -> bool:
        """Check if critique found any critical issues."""
        return any(f.severity == CritiqueSeverity.CRITICAL for f in self.findings)

    def has_major_findings(self) -> bool:
        """Check if critique found any major issues."""
        return any(
            f.severity in [CritiqueSeverity.CRITICAL, CritiqueSeverity.MAJOR]
            for f in self.findings
        )

    def get_critical_findings(self) -> List[CritiqueFinding]:
        """Get all critical findings."""
        return [f for f in self.findings if f.severity == CritiqueSeverity.CRITICAL]

    def get_major_findings(self) -> List[CritiqueFinding]:
        """Get all major findings."""
        return [f for f in self.findings if f.severity == CritiqueSeverity.MAJOR]

    def get_unmet_assumptions(self) -> List[AssumptionCheck]:
        """Get all assumptions that were checked but not met."""
        return [a for a in self.assumption_checks if a.checked and a.met is False]

    def get_unchecked_assumptions(self) -> List[AssumptionCheck]:
        """Get all assumptions that weren't checked."""
        return [a for a in self.assumption_checks if not a.checked]

    def should_regenerate_analysis(self) -> bool:
        """Determine if analysis should be regenerated based on critique."""
        # Regenerate if critical issues or multiple major issues
        return self.has_critical_findings() or len(self.get_major_findings()) >= 2

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage in cell metadata."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnalysisCritique":
        """Create from dictionary loaded from cell metadata."""
        return cls(**data)

    def get_summary(self) -> str:
        """Get human-readable summary of the critique."""
        summary_parts = [
            f"Overall Quality: {self.overall_quality}",
            f"Confidence in Results: {self.confidence_in_results}",
            f"\n{self.summary}",
        ]

        if self.has_critical_findings():
            critical = self.get_critical_findings()
            summary_parts.append(f"\n🚨 CRITICAL ISSUES ({len(critical)}):")
            for finding in critical:
                summary_parts.append(f"  - {finding.title}: {finding.description}")

        major = self.get_major_findings()
        if major:
            summary_parts.append(f"\n⚠️ MAJOR CONCERNS ({len(major)}):")
            for finding in major:
                summary_parts.append(f"  - {finding.title}")

        unmet_assumptions = self.get_unmet_assumptions()
        if unmet_assumptions:
            summary_parts.append(f"\n❌ UNMET ASSUMPTIONS ({len(unmet_assumptions)}):")
            for assumption in unmet_assumptions:
                summary_parts.append(f"  - {assumption.assumption}")

        if self.recommended_improvements:
            summary_parts.append(f"\n💡 RECOMMENDATIONS ({len(self.recommended_improvements)}):")
            for rec in self.recommended_improvements[:3]:  # Show top 3
                summary_parts.append(f"  - {rec}")

        return "\n".join(summary_parts)

    def get_methodology_limitations_section(self) -> str:
        """Generate a limitations section for methodology text."""
        if not self.identified_limitations:
            return ""

        limitations_text = "**Limitations:**\n\n"
        for limitation in self.identified_limitations:
            limitations_text += f"- {limitation}\n"

        # Add unmet assumptions as limitations
        unmet = self.get_unmet_assumptions()
        if unmet:
            limitations_text += "\n**Assumption Violations:**\n\n"
            for assumption in unmet:
                limitations_text += f"- {assumption.assumption}: {assumption.consequences}\n"

        return limitations_text


class CritiqueTrace(BaseModel):
    """Complete trace of the critique process."""
    critique: AnalysisCritique
    llm_provider: str
    llm_model: str
    critique_time_ms: float
    assessment_raw: Optional[str] = Field(
        None,
        description="Raw assessment text from LLM-as-a-judge"
    )

    def get_summary(self) -> str:
        """Get human-readable summary."""
        return f"""
Critique Process ({self.llm_model}, {self.critique_time_ms:.0f}ms):

{self.critique.get_summary()}
"""
