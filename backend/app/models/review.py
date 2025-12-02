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


class CellReview(BaseModel):
    """Review of a single cell's analysis."""
    cell_id: str
    findings: List[ReviewFinding] = Field(default_factory=list)
    overall_quality: str  # "good", "acceptable", "needs_attention"
    reviewed_at: datetime = Field(default_factory=datetime.now)
    reviewer_persona: Optional[str] = None  # Slug of persona that performed review


class ArticleReview(BaseModel):
    """Comprehensive review of entire notebook/article."""
    notebook_id: str
    overall_assessment: str  # Narrative assessment
    rating: int = Field(ge=1, le=5)  # 1-5 stars
    strengths: List[str] = Field(default_factory=list)
    issues: List[ReviewFinding] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
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
