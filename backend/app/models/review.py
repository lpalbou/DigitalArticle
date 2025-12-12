"""
Review data models for Digital Article.

Supports cell-level and article-level scientific review with structured feedback.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class ReviewSeverity(str, Enum):
    """Severity levels for review findings."""
    INFO = "info"           # Suggestions for improvement
    WARNING = "warning"     # Methodological concerns
    CRITICAL = "critical"   # Significant issues to address


class ReviewCategory(str, Enum):
    """Categories of review feedback."""
    METHODOLOGY = "methodology"
    STATISTICS = "statistics"
    INTERPRETATION = "interpretation"
    REPRODUCIBILITY = "reproducibility"
    DATA_QUALITY = "data_quality"
    VISUALIZATION = "visualization"
    CODE_QUALITY = "code_quality"


class ReviewFinding(BaseModel):
    """A single review finding."""
    severity: ReviewSeverity
    category: ReviewCategory
    message: str
    suggestion: Optional[str] = None
    cell_id: Optional[str] = None  # For article-level reviews linking to specific cells
    line_number: Optional[int] = None  # For code-specific findings


# Enhanced Models for SOTA Scientific Review

class DimensionRating(BaseModel):
    """Rating for a specific review dimension."""
    score: int = Field(ge=0, le=5)  # 0-5 stars (0 = Not Assessed)
    label: str  # "Excellent", "Good", "Adequate", "Needs Improvement", "Poor", "Not Assessed"
    summary: str  # Brief justification (markdown supported)


class DataQualityAssessment(BaseModel):
    """Assessment of the data quality and provenance."""
    rating: DimensionRating
    provenance: str  # Where does the data come from? Is it clearly documented? (markdown)
    quality: str  # Data quality assessment (completeness, accuracy, consistency) (markdown)
    quantity: str  # Is the sample size adequate for the analyses performed? (markdown)
    appropriateness: str  # Is the data appropriate for the research question? (markdown)


class ResearchQuestionAssessment(BaseModel):
    """Assessment of the research question/intent quality."""
    rating: DimensionRating
    relevance: str  # Was the subject relevant and significant? (markdown)
    clarity: str  # Was the question clearly stated? (markdown)
    scope: str  # Was the scope appropriate? (markdown)


class MethodologyAssessment(BaseModel):
    """Assessment of the methodological rigor."""
    rating: DimensionRating
    approach_validity: str  # Was the statistical/analytical approach valid? (markdown)
    assumptions: str  # Were assumptions checked and appropriate? (markdown)
    reproducibility: str  # Is the code reproducible? (markdown)


class ResultsCommunicationAssessment(BaseModel):
    """Assessment of results communication quality."""
    rating: DimensionRating
    accuracy: str  # Do results accurately reflect the analysis? (markdown)
    clarity: str  # Are results clearly presented? (markdown)
    completeness: str  # Are all relevant results reported? (markdown)
    methodology_text: str  # Does methodology text explain the approach well? (markdown)


class EnhancedIssue(BaseModel):
    """Enhanced issue with structured feedback for article reviews."""
    severity: ReviewSeverity
    category: ReviewCategory
    title: str  # Short descriptive title
    description: str  # What is the issue? (markdown)
    impact: str  # Why does this matter? What's the scope? (markdown)
    suggestion: str  # How to address this? (actionable, markdown)
    cell_id: Optional[str] = None


class CellReview(BaseModel):
    """Review of a single cell's analysis."""
    cell_id: str
    findings: List[ReviewFinding] = Field(default_factory=list)
    overall_quality: str  # "good", "acceptable", "needs_attention"
    reviewed_at: datetime = Field(default_factory=datetime.now)
    reviewer_persona: Optional[str] = None  # Slug of persona that performed review


class ArticleReview(BaseModel):
    """Comprehensive review of entire notebook/article.

    Supports both legacy and enhanced review formats for backward compatibility.
    Enhanced format includes dimensional assessments following SOTA journal review practices.
    """
    notebook_id: str

    # Enhanced Format (SOTA Scientific Review) - Optional for backward compatibility
    data_quality: Optional[DataQualityAssessment] = None  # NEW: First dimension
    research_question: Optional[ResearchQuestionAssessment] = None
    methodology: Optional[MethodologyAssessment] = None
    results_communication: Optional[ResultsCommunicationAssessment] = None
    recommendation: Optional[str] = None  # "Accept", "Minor Revisions", "Major Revisions", "Reject"

    # Overall Assessment (used in both legacy and enhanced formats)
    overall_assessment: str  # Narrative assessment (markdown supported)
    rating: int = Field(ge=1, le=5, default=3)  # Overall 1-5 stars (legacy field, kept for compatibility)

    # Detailed Feedback (enhanced format uses EnhancedIssue, legacy uses ReviewFinding)
    strengths: List[str] = Field(default_factory=list)  # Key strengths (markdown supported)
    issues: List[ReviewFinding] = Field(default_factory=list)  # Legacy format issues
    enhanced_issues: List[EnhancedIssue] = Field(default_factory=list)  # Enhanced format issues
    recommendations: List[str] = Field(default_factory=list)  # Suggestions (markdown supported)

    # Metadata
    reviewed_at: datetime = Field(default_factory=datetime.now)
    reviewer_persona: Optional[str] = None  # Slug of persona that performed review


# Review Settings Models

class ReviewPhaseSettings(BaseModel):
    """Settings for individual review phases."""
    intent_enabled: bool = True
    implementation_enabled: bool = True
    results_enabled: bool = True


class ReviewDisplaySettings(BaseModel):
    """User preferences for review display."""
    show_severity: str = "all"  # "all", "warnings_and_critical", "critical_only"
    auto_collapse: bool = False  # Auto-collapse review panels
    show_suggestions: bool = True  # Show actionable suggestions


class ReviewSettings(BaseModel):
    """Global review configuration (stored in user settings)."""
    auto_review_enabled: bool = False
    phases: ReviewPhaseSettings = Field(default_factory=ReviewPhaseSettings)
    display: ReviewDisplaySettings = Field(default_factory=ReviewDisplaySettings)
    review_style: str = "constructive"  # "constructive", "brief", "detailed"


# API Request/Response Models

class ReviewCellRequest(BaseModel):
    """Request to review a specific cell."""
    cell_id: str
    notebook_id: str
    force: bool = False  # Force re-review even if cached


class ReviewArticleRequest(BaseModel):
    """Request to review entire article."""
    notebook_id: str
    force: bool = False  # Force re-review even if cached


class ReviewSettingsUpdateRequest(BaseModel):
    """Request to update review settings."""
    auto_review_enabled: Optional[bool] = None
    phases: Optional[ReviewPhaseSettings] = None
    display: Optional[ReviewDisplaySettings] = None
    review_style: Optional[str] = None
