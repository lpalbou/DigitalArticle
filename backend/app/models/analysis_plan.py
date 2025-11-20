"""
Data models for analysis planning and reasoning.

These models represent the structured output of the analysis planning phase,
capturing the LLM's reasoning about what analysis to perform and why.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class IssueSeverity(str, Enum):
    """Severity levels for validation issues."""
    CRITICAL = "critical"  # Analysis should not proceed
    WARNING = "warning"    # Analysis can proceed with caution
    INFO = "info"          # Informational note


class IssueType(str, Enum):
    """Types of logical/analytical issues."""
    CIRCULAR_REASONING = "circular_reasoning"
    DATA_MISMATCH = "data_mismatch"
    TEMPORAL_LOGIC = "temporal_logic"
    SAMPLE_SIZE = "sample_size"
    METHOD_MISMATCH = "method_mismatch"
    MISSING_ASSUMPTIONS = "missing_assumptions"
    CONFOUNDING = "confounding"


class LogicalIssue(BaseModel):
    """Represents a logical or analytical issue identified during planning."""
    severity: IssueSeverity
    type: IssueType
    message: str = Field(..., description="Short summary of the issue")
    explanation: str = Field(..., description="Detailed explanation of why this is an issue")
    suggestion: str = Field(..., description="Suggested fix or alternative approach")
    affected_variables: List[str] = Field(default_factory=list, description="Variables involved in this issue")


class AnalysisPlan(BaseModel):
    """
    Structured plan for data analysis, created before code generation.

    This represents the LLM's reasoning about:
    - What the user is trying to learn
    - What variables/methods are appropriate
    - What assumptions are being made
    - What potential issues exist
    """

    # Core intent and approach
    user_intent: str = Field(..., description="What the user is trying to learn/discover")
    research_question: str = Field(..., description="The specific question being answered")
    analysis_type: str = Field(
        ...,
        description="Type of analysis: exploration, prediction, comparison, hypothesis_test, etc."
    )

    # Variable identification
    target_variable: Optional[str] = Field(
        None,
        description="The outcome/dependent variable (what we're trying to explain/predict)"
    )
    predictor_variables: List[str] = Field(
        default_factory=list,
        description="The input/independent variables (what might influence the target)"
    )
    derived_variables: List[str] = Field(
        default_factory=list,
        description="Variables that need to be created/derived from existing data"
    )

    # Methodological approach
    suggested_method: str = Field(
        ...,
        description="Recommended statistical/ML method for this analysis"
    )
    method_rationale: str = Field(
        ...,
        description="Why this method is appropriate for the data and question"
    )
    alternative_methods: List[str] = Field(
        default_factory=list,
        description="Other valid approaches that could be considered"
    )

    # Assumptions and limitations
    assumptions: List[str] = Field(
        default_factory=list,
        description="Statistical/analytical assumptions being made"
    )
    limitations: List[str] = Field(
        default_factory=list,
        description="Known limitations of this analysis approach"
    )
    confounders: List[str] = Field(
        default_factory=list,
        description="Potential confounding variables to consider"
    )

    # Data validation
    data_requirements: List[str] = Field(
        default_factory=list,
        description="Required data characteristics (sample size, data types, etc.)"
    )
    data_quality_checks: List[str] = Field(
        default_factory=list,
        description="Checks to perform before analysis (missing values, outliers, etc.)"
    )

    # Validation issues
    validation_issues: List[LogicalIssue] = Field(
        default_factory=list,
        description="Logical or analytical issues identified during planning"
    )

    # Metadata
    confidence_level: str = Field(
        default="medium",
        description="Confidence in this analysis plan: low, medium, high"
    )
    requires_user_review: bool = Field(
        default=False,
        description="Whether this plan should be reviewed by user before execution"
    )

    def has_critical_issues(self) -> bool:
        """Check if plan has any critical issues that should block execution."""
        return any(issue.severity == IssueSeverity.CRITICAL for issue in self.validation_issues)

    def get_critical_issues(self) -> List[LogicalIssue]:
        """Get all critical issues."""
        return [issue for issue in self.validation_issues if issue.severity == IssueSeverity.CRITICAL]

    def get_warnings(self) -> List[LogicalIssue]:
        """Get all warnings."""
        return [issue for issue in self.validation_issues if issue.severity == IssueSeverity.WARNING]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage in cell metadata."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnalysisPlan":
        """Create from dictionary loaded from cell metadata."""
        return cls(**data)

    def get_summary(self) -> str:
        """Get human-readable summary of the plan."""
        summary_parts = [
            f"Research Question: {self.research_question}",
            f"Analysis Type: {self.analysis_type}",
        ]

        if self.target_variable:
            summary_parts.append(f"Target Variable: {self.target_variable}")

        if self.predictor_variables:
            summary_parts.append(f"Predictors: {', '.join(self.predictor_variables)}")

        summary_parts.append(f"Suggested Method: {self.suggested_method}")

        if self.has_critical_issues():
            critical = self.get_critical_issues()
            summary_parts.append(f"\n🚨 CRITICAL ISSUES ({len(critical)}):")
            for issue in critical:
                summary_parts.append(f"  - {issue.message}")

        warnings = self.get_warnings()
        if warnings:
            summary_parts.append(f"\n⚠️ WARNINGS ({len(warnings)}):")
            for warning in warnings:
                summary_parts.append(f"  - {warning.message}")

        return "\n".join(summary_parts)


class ReasoningStep(BaseModel):
    """Represents a single step in the multi-turn reasoning process."""
    step_number: int
    step_type: str  # intent_clarification, variable_identification, method_selection, validation
    prompt: str
    response: str
    reasoning: str
    confidence: str = "medium"  # low, medium, high


class ReasoningTrace(BaseModel):
    """Complete trace of the reasoning process that led to an analysis plan."""
    steps: List[ReasoningStep] = Field(default_factory=list)
    final_plan: AnalysisPlan
    total_reasoning_time_ms: float
    llm_provider: str
    llm_model: str

    def add_step(self, step: ReasoningStep):
        """Add a reasoning step to the trace."""
        self.steps.append(step)

    def get_summary(self) -> str:
        """Get human-readable summary of reasoning process."""
        return f"""
Reasoning Process ({len(self.steps)} steps, {self.total_reasoning_time_ms:.0f}ms):

{chr(10).join(f"{i+1}. {step.step_type}: {step.reasoning}" for i, step in enumerate(self.steps))}

Final Plan:
{self.final_plan.get_summary()}
"""
