# Persona and Review System - Architecture Documentation

## Executive Summary

The Persona and Review system provides a clean separation of concerns for Digital Article:

- **Personas**: Domain experts who **write** the article (Clinical, Genomics, RWD, etc.)
- **Review**: Quality control system that **evaluates** the article and suggests improvements

This architecture emerged from user feedback that correctly identified "reviewer" as a process, not a domain expertise.

## Core Architectural Principles

### 1. Single Responsibility Principle

**Personas** (WHO writes):
- Purpose: Define domain expertise for article generation
- Selection: ONE persona per notebook (radio select)
- Examples: Generic, Clinical, Genomics, RWD, Medical Imaging
- Impact: Influences code generation, methodology writing, terminology

**Review** (HOW to improve):
- Purpose: Automated quality checks and improvement suggestions
- Implementation: ReviewService + ReviewSettings
- Phases: Intent review, Implementation review, Results review
- Impact: Provides feedback without changing the generation process

### 2. Separation of Concerns

```
┌──────────────────────────────────────┐
│ PERSONA SYSTEM (Domain Expertise)    │
├──────────────────────────────────────┤
│ • Defines WHO writes the article    │
│ • Clinical, Genomics, RWD, etc.      │
│ • Injects domain-specific guidance  │
│ • One persona per notebook          │
│ • Storage: notebook.metadata         │
│   ['personas']['base_persona']       │
└──────────────────────────────────────┘

┌──────────────────────────────────────┐
│ REVIEW SYSTEM (Quality Control)      │
├──────────────────────────────────────┤
│ • Evaluates article quality          │
│ • Suggests improvements              │
│ • 3 phases: intent, impl, results    │
│ • Works independently of persona     │
│ • Storage: notebook.metadata         │
│   ['review_settings']                │
└──────────────────────────────────────┘
```

## Persona System Implementation

### Data Models

**Backend** (`backend/app/models/persona.py`):
```python
class PersonaCategory(str, Enum):
    BASE = "base"      # Generic, Clinical, Genomics, RWD, Medical Imaging
    DOMAIN = "domain"  # Future: specialized sub-domains
    ROLE = "role"      # Future: modifiers (unused for now)
    CUSTOM = "custom"  # User-created personas

class Persona(BaseModel):
    id: UUID
    name: str
    slug: str  # URL-safe identifier
    description: str
    icon: str  # Lucide icon name
    color: str  # Hex color for UI
    category: PersonaCategory
    priority: int = 100  # For future combination logic
    is_system: bool = False  # System personas are read-only
    is_active: bool = True  # Inactive personas hidden from UI

    # Domain expertise
    expertise_description: str
    domain_context: str
    methodology_style: str

    # Guidance per scope
    guidance: List[PersonaGuidance] = []

    # Library preferences
    preferred_libraries: List[str] = []
    avoid_libraries: List[str] = []

    # Metadata
    created_at: datetime
    updated_at: datetime
    created_by: str
    version: int
    tags: List[str] = []

class PersonaSelection(BaseModel):
    """Stored in notebook.metadata['personas']"""
    base_persona: str  # Slug of selected persona (required)
    domain_personas: List[str] = []  # UNUSED (for future)
    role_modifier: Optional[str] = None  # UNUSED (for future)
    custom_overrides: Dict[str, Any] = {}  # UNUSED (for future)
```

**Frontend** (`frontend/src/types/persona.ts`):
- TypeScript types mirror backend models
- Ensures type safety across API boundary

### System Personas

**Location**: `data/personas/system/*.json`

**Currently Active**:
1. **Generic Data Analyst** (`generic.json`)
   - Category: base
   - Priority: 100
   - General-purpose data analysis
   - Libraries: pandas, numpy, matplotlib, seaborn

2. **Clinical Data Scientist** (`clinical.json`)
   - Category: base
   - Priority: 50
   - Clinical trials, CDISC standards, regulatory compliance
   - Libraries: pandas, lifelines, statsmodels, tableone

**Inactive** (architectural change):
3. **Scientific Reviewer** (`reviewer.json`)
   - Set `is_active: false`
   - Reason: Reviewer is a process, not a domain expert
   - Review functionality moved to Review system

**Planned (Phase 2)**:
4. Real-World Data (RWD)
5. Genomics (bulk RNA-seq, single-cell, spatial, etc.)
6. Medical Imaging (CT, MRI, PET scans)

### Services

**PersonaService** (`backend/app/services/persona_service.py`):
```python
class PersonaService:
    def __init__(self, workspace_dir: Optional[str] = None):
        # Auto-detects project root for robust path resolution
        if workspace_dir is None:
            current_file = Path(__file__).resolve()
            backend_dir = current_file.parent.parent.parent
            project_root = backend_dir.parent
            workspace_dir = str(project_root / "data")

        self.workspace_dir = Path(workspace_dir)
        self.system_personas_dir = self.workspace_dir / "personas" / "system"
        self.custom_personas_dir = self.workspace_dir / "personas" / "custom"

    # CRUD Operations
    def get_persona(self, slug: str, username: Optional[str] = None) -> Optional[Persona]
    def list_personas(self, username: Optional[str] = None,
                      category: Optional[PersonaCategory] = None,
                      include_inactive: bool = False) -> List[Persona]
    def create_persona(self, request: PersonaCreateRequest, username: str) -> Persona
    def update_persona(self, slug: str, request: PersonaUpdateRequest, username: str) -> Persona
    def delete_persona(self, slug: str, username: str) -> None

    # Combination Logic (for future multi-persona support)
    def combine_personas(self, selection: PersonaSelection, username: Optional[str] = None) -> PersonaCombination

    # Prompt Building
    def build_system_prompt_addition(self, combination: PersonaCombination, scope: PersonaScope) -> str
```

**Key Fixes**:
- **Path Resolution**: Auto-detects project root using `__file__`
- **Logging**: Comprehensive logging for debugging
- **Error Handling**: Proper error messages, no silent failures

### API Endpoints

**REST API** (`backend/app/api/personas.py`):
```
GET    /api/personas                     - List all personas
GET    /api/personas/{slug}              - Get specific persona
POST   /api/personas                     - Create custom persona
PUT    /api/personas/{slug}              - Update custom persona
DELETE /api/personas/{slug}              - Delete custom persona
POST   /api/personas/combine             - Preview combination
GET    /api/personas/notebooks/{id}/personas  - Get notebook selection
PUT    /api/personas/notebooks/{id}/personas  - Update notebook selection
```

### System Prompt Integration

**LLM Service** (`backend/app/services/llm_service.py`):
```python
def _build_system_prompt(self, context: Optional[Dict[str, Any]] = None) -> str:
    """Build system prompt with persona guidance."""
    # Extract persona combination if present
    persona_guidance = ""
    if context and 'persona_combination' in context:
        from ..services.persona_service import PersonaService
        from ..models.persona import PersonaScope

        persona_service = PersonaService()
        persona_combination = context['persona_combination']
        persona_guidance = persona_service.build_system_prompt_addition(
            persona_combination,
            PersonaScope.CODE_GENERATION
        )

    # Inject after base prompt
    if persona_guidance:
        base_prompt += "\n\n" + "="*80 + "\n"
        base_prompt += "SPECIALIZED PERSONA GUIDANCE:\n"
        base_prompt += persona_guidance

    return base_prompt
```

**Notebook Service** (`backend/app/services/notebook_service.py`):
```python
def _build_execution_context(self, notebook: Notebook, current_cell: Cell) -> Dict[str, Any]:
    """Load persona from notebook metadata and inject into context."""
    context = {}

    # Load and combine personas if selected for notebook
    try:
        if 'personas' in notebook.metadata and notebook.metadata['personas']:
            persona_data = notebook.metadata['personas']
            persona_selection = PersonaSelection(**persona_data)

            persona_service = PersonaService()
            persona_combination = persona_service.combine_personas(persona_selection)

            context['persona_combination'] = persona_combination
            logger.info(f"Loaded persona: {persona_combination.source_personas}")
    except Exception as e:
        logger.warning(f"Could not load persona: {e}")

    return context
```

### UI Components

**PersonaTab** (`frontend/src/components/PersonaTab.tsx`):
- Simplified UI - single radio select
- Removed: domain personas, role modifiers (overcomplicated)
- Shows: Base personas + custom personas
- Selection stored in `notebook.metadata['personas']['base_persona']`

**PersonaCard** (`frontend/src/components/PersonaCard.tsx`):
- Visual card with icon, name, description
- Color-coded by persona
- Radio select for single selection

**PersonaEditor** (`frontend/src/components/PersonaEditor.tsx`):
- MVP implementation for custom personas
- Basic fields: name, slug, description, icon, color
- Future: Advanced guidance templates, library preferences

## Review System Implementation

### Architecture

**Separation from Personas**:
- Review is **independent** of persona selection
- Works as quality control layer
- Uses ReviewService (orchestration) + review templates

### Data Models

**Backend** (`backend/app/models/review.py`):
```python
class ReviewSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

class ReviewCategory(str, Enum):
    METHODOLOGY = "methodology"
    STATISTICS = "statistics"
    INTERPRETATION = "interpretation"
    REPRODUCIBILITY = "reproducibility"
    DATA_QUALITY = "data_quality"
    VISUALIZATION = "visualization"
    CODE_QUALITY = "code_quality"

class ReviewFinding(BaseModel):
    severity: ReviewSeverity
    category: ReviewCategory
    message: str
    suggestion: Optional[str] = None
    cell_id: Optional[str] = None
    line_number: Optional[int] = None

class CellReview(BaseModel):
    cell_id: str
    findings: List[ReviewFinding]
    overall_quality: str  # good, acceptable, needs_attention
    reviewed_at: datetime
    reviewer_persona: Optional[str] = None

class ArticleReview(BaseModel):
    notebook_id: str
    overall_assessment: str
    rating: int  # 1-5 stars
    strengths: List[str]
    issues: List[ReviewFinding]
    recommendations: List[str]
    reviewed_at: datetime

class ReviewSettings(BaseModel):
    """Stored in notebook.metadata['review_settings']"""
    auto_review_enabled: bool = False
    phases: ReviewPhaseSettings
    display: ReviewDisplaySettings
    review_style: str = 'constructive'  # constructive, brief, detailed
```

### Services

**ReviewService** (`backend/app/services/review_service.py`):
```python
class ReviewService:
    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm_service = llm_service or LLMService()
        self.logger = logging.getLogger(__name__)

    # Cell-level review
    async def review_cell(self, cell: Cell, notebook: Notebook,
                         persona_combination: Optional[PersonaCombination] = None) -> CellReview

    # Article-level review
    async def review_article(self, notebook: Notebook,
                            persona_combination: Optional[PersonaCombination] = None) -> ArticleReview

    # Review prompts (uses templates)
    def _build_review_prompt(self, phase: ReviewPhase, context: Dict[str, Any]) -> str
```

**Key Features**:
- Uses LLM to analyze code/results
- Parses structured findings with severity
- Stores reviews in cell/notebook metadata
- Independent of persona selection

### UI Components

**ReviewSettingsTab** (`frontend/src/components/ReviewSettingsTab.tsx`):
- **Auto-review toggle**: Enable/disable automatic review after execution
- **Phase selection**: Intent, Implementation, Results (checkboxes)
- **Severity filter**: All / Warnings+Critical / Critical only (radio)
- **Display settings**: Auto-collapse, Show suggestions (checkboxes)
- **Review style**: Constructive / Brief / Detailed (dropdown)
- **Save button**: Stores settings in notebook metadata

**Future Components** (not yet implemented):
- ReviewFeedback (cell-level review display)
- ArticleReviewModal (full article review report)
- Review button in notebook toolbar

## Storage Schema

### Notebook Metadata Structure

```json
{
  "metadata": {
    "personas": {
      "base_persona": "clinical",  // Single persona slug
      "domain_personas": [],       // UNUSED (future)
      "role_modifier": null,       // UNUSED (future)
      "custom_overrides": {}       // UNUSED (future)
    },
    "review_settings": {
      "auto_review_enabled": true,
      "phases": {
        "intent_enabled": true,
        "implementation_enabled": true,
        "results_enabled": true
      },
      "display": {
        "show_severity": "warnings_and_critical",
        "auto_collapse": false,
        "show_suggestions": true
      },
      "review_style": "constructive"
    }
  }
}
```

### Cell Metadata (Review Results)

```json
{
  "metadata": {
    "review": {
      "cell_id": "uuid",
      "findings": [
        {
          "severity": "warning",
          "category": "statistics",
          "message": "Sample size (n=15) may be too small for reliable t-test",
          "suggestion": "Consider non-parametric alternatives (Mann-Whitney U test)"
        }
      ],
      "overall_quality": "acceptable",
      "reviewed_at": "2025-12-02T12:34:56"
    }
  }
}
```

## Future Enhancements

### Phase 2: Additional Personas
1. **Real-World Data (RWD)**
   - Observational studies, propensity scores
   - Libraries: statsmodels, scikit-learn, lifelines

2. **Genomics**
   - Bulk RNA-seq, single-cell, spatial transcriptomics
   - Libraries: scanpy, seurat, DESeq2 equivalents

3. **Medical Imaging**
   - CT, MRI, PET scan analysis
   - Libraries: SimpleITK, nibabel, radiomics

### Phase 3: Review UI Integration
1. **ReviewFeedback Component**
   - Cell-level review display (collapsible)
   - Severity-coded findings (info/warning/critical)
   - Integration with cell editor

2. **ArticleReviewModal**
   - Full article synthesis review
   - Rating, strengths, issues, recommendations
   - Export to PDF option

3. **Enhanced Execution Status**
   - Phase indicators (Planning → Generating → Executing → Reviewing)
   - Replace simple "generating..." spinner
   - Show current phase in real-time

## Design Decisions & Rationale

### Why Separate Persona and Review?

**Original Confusion**: Reviewer was initially a "persona" alongside Clinical and Generic
**User Insight**: "Reviewer can't be a persona as reviewer doesn't write the article"
**Correct Architecture**:
- Personas = WHO writes (domain experts)
- Review = HOW to improve (quality control)

### Why Single Persona Selection?

**Original Design**: Multi-select with combinations (base + domains + role)
**User Feedback**: "We can only select 1 persona, not 2"
**Simplification Benefits**:
- Cleaner UI (no confusion about combinations)
- Simpler mental model (pick your domain expert)
- Easier to maintain (no combination logic complexity)
- Future-proof (can add combinations if needed)

### Why Keep PersonaSelection Structure?

**Option A**: Simplify to just `persona: str`
**Option B**: Keep structure, don't use extra fields
**Chosen**: B - Keep structure
**Reasoning**:
- Backward compatible with existing notebooks
- Allows future extensibility without breaking changes
- Current code already uses `base_persona` field correctly

### Why Auto-detect Project Root?

**Problem**: Relative path `"data"` failed depending on startup directory
**Solution**: Auto-detect from `__file__` location
**Benefits**:
- Works from any startup directory
- No hardcoded paths
- Portable across systems
- Proper production pattern

## Testing Strategy

### Backend Tests
- PersonaService CRUD operations
- Persona combination logic
- System prompt injection
- Path resolution robustness
- ReviewService functionality

### Frontend Tests
- PersonaTab selection flow
- ReviewSettingsTab save flow
- Integration with SettingsModal
- Persona card rendering

### Integration Tests
- End-to-end persona selection
- Notebook metadata persistence
- LLM prompt injection verification
- Review flow (when implemented)

## Common Issues & Solutions

### Issue: "No Personas Available" in UI

**Cause**: PersonaService used relative path `"data"`
**Solution**: Auto-detect project root in PersonaService.__init__()
**Verification**: Check backend logs for "📁 PersonaService initialized with workspace: ..."

### Issue: Reviewer shows in persona list

**Cause**: `is_active: true` in reviewer.json
**Solution**: Set `is_active: false` in reviewer.json
**Verification**: Only Generic and Clinical show in UI

### Issue: Can't select multiple personas

**Not a bug**: By design, only one persona per notebook
**Rationale**: Simpler, cleaner architecture per user feedback

## Deployment Checklist

- [ ] Backend restarted with new PersonaService code
- [ ] Persona JSON files in `data/personas/system/`
- [ ] Reviewer persona set to `is_active: false`
- [ ] Frontend rebuilt with updated components
- [ ] API endpoint `/api/personas` returns personas
- [ ] Settings modal shows 4 tabs
- [ ] Persona tab shows only active personas
- [ ] Review tab shows settings UI

## API Quick Reference

```bash
# List personas
curl http://localhost:8000/api/personas

# Get specific persona
curl http://localhost:8000/api/personas/clinical

# Get notebook persona selection
curl http://localhost:8000/api/personas/notebooks/{notebook_id}/personas

# Update notebook persona selection
curl -X PUT http://localhost:8000/api/personas/notebooks/{notebook_id}/personas \
  -H "Content-Type: application/json" \
  -d '{"base_persona": "clinical"}'
```

## References

- Original Implementation Plan: `.claude/plans/refactored-coalescing-quilt.md`
- Path Fix Documentation: `PERSONA_UI_FIX.md`
- Backend Service: `backend/app/services/persona_service.py`
- Frontend Components: `frontend/src/components/PersonaTab.tsx`, `ReviewSettingsTab.tsx`
- Data Models: `backend/app/models/persona.py`, `backend/app/models/review.py`
