"""
Persona data models for Digital Article.

Personas define specialized AI assistants with domain expertise and behavioral characteristics.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class PersonaCategory(str, Enum):
    """Categories of personas for organization and filtering."""
    BASE = "base"           # Foundation personas (Generic, Clinical, Reviewer)
    DOMAIN = "domain"       # Domain-specific (RWD, Medical Imaging, Genomics)
    ROLE = "role"          # Role-based modifiers (conservative, exploratory)
    CUSTOM = "custom"       # User-created personas


class PersonaScope(str, Enum):
    """Where the persona guidance applies."""
    CODE_GENERATION = "code_generation"
    METHODOLOGY = "methodology"
    CHAT = "chat"
    ABSTRACT = "abstract"
    REVIEW = "review"
    ALL = "all"


class ReviewPhase(str, Enum):
    """Review phases for Reviewer persona."""
    INTENT = "intent"           # Review the question/intent
    IMPLEMENTATION = "implementation"  # Review the HOW (code)
    RESULTS = "results"         # Review the WHAT (outputs)
    SYNTHESIS = "synthesis"     # Global synthesis


class PersonaGuidance(BaseModel):
    """Guidance for a specific scope."""
    scope: PersonaScope
    system_prompt_addition: str = ""      # Appended to system prompt
    user_prompt_prefix: str = ""          # Prepended to user prompt
    user_prompt_suffix: str = ""          # Appended to user prompt
    constraints: List[str] = Field(default_factory=list)  # Hard constraints
    preferences: List[str] = Field(default_factory=list)  # Soft preferences
    examples: List[str] = Field(default_factory=list)     # Few-shot examples


class ReviewCapability(BaseModel):
    """Special capabilities for Reviewer persona."""
    phase: ReviewPhase
    prompt_template: str
    output_format: str  # structured, narrative, checklist
    severity_levels: List[str] = Field(default_factory=lambda: ["info", "warning", "critical"])


class Persona(BaseModel):
    """Complete persona definition."""

    # Identity
    id: UUID = Field(default_factory=uuid4)
    name: str                              # Display name
    slug: str                              # URL-safe identifier
    description: str = ""                  # Short description
    icon: str = "user"                     # Lucide icon name
    color: str = "#6366f1"                # Brand color (hex)

    # Classification
    category: PersonaCategory = PersonaCategory.CUSTOM
    priority: int = 100                    # Lower = higher priority in conflicts
    is_system: bool = False               # True for built-in personas
    is_active: bool = True                # Can be disabled

    # Expertise & Context
    expertise_description: str = ""        # What this persona knows
    domain_context: str = ""               # Domain-specific background
    methodology_style: str = ""            # How methodology text should read

    # Guidance per scope
    guidance: List[PersonaGuidance] = Field(default_factory=list)

    # Tool/Library preferences
    preferred_libraries: List[str] = Field(default_factory=list)
    avoid_libraries: List[str] = Field(default_factory=list)
    preferred_methods: List[str] = Field(default_factory=list)

    # Reviewer-specific (only for Reviewer category)
    review_capabilities: List[ReviewCapability] = Field(default_factory=list)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    created_by: str = ""                   # Username
    version: int = 1
    tags: List[str] = Field(default_factory=list)

    # Compatibility
    compatible_with: List[str] = Field(default_factory=list)  # Other persona slugs
    incompatible_with: List[str] = Field(default_factory=list)


class PersonaSelection(BaseModel):
    """Persona selection for a notebook (stored in notebook.metadata['personas'])."""
    base_persona: str                      # Slug of base persona (required)
    domain_personas: List[str] = Field(default_factory=list)  # Additional domains
    role_modifier: Optional[str] = None    # Optional role modifier
    custom_overrides: Dict[str, Any] = Field(default_factory=dict)  # Per-notebook tweaks


class PersonaCombination(BaseModel):
    """Result of combining multiple personas."""
    effective_guidance: Dict[PersonaScope, PersonaGuidance]
    source_personas: List[str]             # Slugs used
    conflict_resolutions: List[str] = Field(default_factory=list)  # Log of resolved conflicts


# API Request/Response Models

class PersonaCreateRequest(BaseModel):
    """Request to create a new custom persona."""
    name: str
    slug: str
    description: str = ""
    icon: str = "user"
    color: str = "#6366f1"
    category: PersonaCategory = PersonaCategory.CUSTOM
    priority: int = 100
    expertise_description: str = ""
    domain_context: str = ""
    methodology_style: str = ""
    guidance: List[PersonaGuidance] = Field(default_factory=list)
    preferred_libraries: List[str] = Field(default_factory=list)
    avoid_libraries: List[str] = Field(default_factory=list)
    preferred_methods: List[str] = Field(default_factory=list)
    review_capabilities: List[ReviewCapability] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    compatible_with: List[str] = Field(default_factory=list)
    incompatible_with: List[str] = Field(default_factory=list)


class PersonaUpdateRequest(BaseModel):
    """Request to update an existing custom persona."""
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None
    expertise_description: Optional[str] = None
    domain_context: Optional[str] = None
    methodology_style: Optional[str] = None
    guidance: Optional[List[PersonaGuidance]] = None
    preferred_libraries: Optional[List[str]] = None
    avoid_libraries: Optional[List[str]] = None
    preferred_methods: Optional[List[str]] = None
    review_capabilities: Optional[List[ReviewCapability]] = None
    tags: Optional[List[str]] = None
    compatible_with: Optional[List[str]] = None
    incompatible_with: Optional[List[str]] = None


class PersonaSelectionUpdateRequest(BaseModel):
    """Request to update notebook persona selection."""
    base_persona: str
    domain_personas: List[str] = Field(default_factory=list)
    role_modifier: Optional[str] = None
    custom_overrides: Dict[str, Any] = Field(default_factory=dict)
