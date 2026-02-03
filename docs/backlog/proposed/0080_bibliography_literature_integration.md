# Backlog Item (Proposed)

## Title
Bibliography & Literature Integration for Article Context

## Backlog ID
0080

## Priority
- **P1 (proposed)**: High user value. Transforms Digital Article from "code executor" to "research assistant" by grounding analyses in existing literature.

## Date / Time
2026-02-01

## Short Summary
Integrate bibliography/literature awareness into Digital Article to:
1. **Introduction writing**: Generate proper introductions grounded in field literature
2. **Analysis guidance**: Inform code generation with established methodologies, expected results, and domain knowledge
3. **Bibliography section**: Auto-generate a references section in the rendered article/PDF

This makes Digital Article outputs closer to publication-ready academic papers.

## Key Goals
- Allow users to specify field/topic of interest for the article
- Automatically retrieve relevant literature (papers, methods, benchmarks)
- Use literature context to improve LLM prompts for code generation
- Generate a bibliography section in exports (PDF, HTML)

## Scope

### To do
- Add "Research Context" section to notebook metadata (field, keywords, seed papers)
- Implement literature search integration (Semantic Scholar, PubMed, arXiv APIs)
- Store retrieved references in notebook metadata
- Inject literature context into LLM prompts (code generation, methodology)
- Generate "Introduction" section based on literature review
- Generate "References" section in PDF export
- UI for managing bibliography (add/remove/search papers)

### NOT to do
- Full citation management system (not Zotero replacement)
- PDF parsing of full papers (use abstracts/metadata only)
- Manual citation formatting (auto-format based on style)

## Dependencies

### Backlog dependencies (ordering)
- Can be done independently
- Would benefit from:
  - [`0035_improved_scientific_methodology_generation.md`](0035_improved_scientific_methodology_generation.md) - Synergy with methodology improvements

### ADR dependencies (must comply)
- **All ADRs are mandatory**: [`docs/adr/README.md`](../../adr/README.md)
- **Primary ADR dependencies**:
  - [`ADR 0001`](../../adr/0001-article-first-mixed-audience.md) - Article-first means proper academic structure
  - [`ADR 0007`](../../adr/0007-permissive-licenses-and-minimal-dependencies.md) - Use permissive API clients

### Points of vigilance (during execution)
- Rate limits on academic APIs (Semantic Scholar, PubMed)
- Avoid hallucinated citations - only include papers that actually exist
- DOI verification for all included references
- Privacy: don't leak user research topics to external services without consent

## References (source of truth)
- `backend/app/models/notebook.py` - Notebook metadata
- `backend/app/services/llm_service.py` - Prompt context injection
- `backend/app/services/pdf_service_scientific.py` - PDF generation

## Proposal (initial; invites deeper thought)

### Context / constraints
- Academic papers have: Abstract → Introduction → Methods → Results → Discussion → References
- Digital Article currently generates: Methodology (per cell) → Results
- Missing: Introduction (literature context) and References (bibliography)
- Literature APIs are free but rate-limited (Semantic Scholar: 100 req/5min)

### Design options considered (with long-term consequences)

#### Option A: User provides BibTeX manually
- **Pros**: Simple; no API integration; user controls sources
- **Cons**: High friction; users may not have BibTeX ready; no auto-discovery
- **Long-term consequences**: Limited adoption; not "AI-assisted"

#### Option B: Semantic Scholar API integration (recommended)
```
User specifies: "survival analysis in oncology clinical trials"
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ Literature Service                                           │
│  1. Search Semantic Scholar API for relevant papers          │
│  2. Retrieve top N papers (title, authors, abstract, DOI)    │
│  3. Store in notebook.metadata.bibliography                  │
│  4. Inject abstracts into LLM context for code generation    │
└──────────────────────────────────────────────────────────────┘
       │
       ▼
LLM sees: "Related work: [Paper1] showed that... [Paper2] found..."
       │
       ▼
Generated code is informed by field best practices
```
- **Pros**: Auto-discovery; real papers with DOIs; rich metadata
- **Cons**: Requires API key (free tier available); rate limits
- **Long-term consequences**: High-quality, verifiable citations

#### Option C: RAG with embedded paper corpus
- **Pros**: Offline; deeper understanding of paper content
- **Cons**: Requires large corpus; embedding cost; maintenance
- **Long-term consequences**: Most powerful but highest complexity

### Recommended approach (current best choice)

**Option B (Semantic Scholar API)** with these components:

1. **Notebook Metadata Extension**
```python
class NotebookMetadata(BaseModel):
    # Existing fields...
    research_context: Optional[ResearchContext] = None

class ResearchContext(BaseModel):
    field: str  # e.g., "oncology", "genomics"
    keywords: List[str]  # e.g., ["survival analysis", "Kaplan-Meier"]
    seed_papers: List[str]  # DOIs or Semantic Scholar IDs
    bibliography: List[Reference]  # Retrieved papers

class Reference(BaseModel):
    title: str
    authors: List[str]
    year: int
    doi: Optional[str]
    abstract: Optional[str]
    venue: Optional[str]  # Journal/conference
    semantic_scholar_id: Optional[str]
    citation_key: str  # e.g., "Smith2023"
```

2. **Literature Service**
```python
class LiteratureService:
    async def search_papers(self, query: str, limit: int = 10) -> List[Reference]: ...
    async def get_paper_by_doi(self, doi: str) -> Reference: ...
    async def expand_bibliography(self, seed_dois: List[str]) -> List[Reference]: ...
    def format_citations(self, refs: List[Reference], style: str = "APA") -> str: ...
```

3. **LLM Context Injection**
```python
# In _build_system_prompt():
if notebook.metadata.research_context:
    context = notebook.metadata.research_context
    literature_context = f"""
    FIELD CONTEXT: {context.field}
    
    RELEVANT LITERATURE:
    {format_abstracts(context.bibliography[:5])}
    
    Use established methodologies from this field.
    Cite relevant papers when applicable.
    """
```

4. **PDF Export Enhancement**
```python
# In ScientificPDFService:
def _render_references_section(self, bibliography: List[Reference]) -> str:
    """Generate APA-formatted references section."""
    ...
```

5. **UI Components**
- "Research Context" tab in notebook settings
- Search box to find and add papers
- Bibliography list with remove/reorder
- "Generate Introduction" button

### Testing plan (A/B/C)

- **A (mock / conceptual)**:
  - Mock Semantic Scholar responses
  - Verify bibliography stored in notebook metadata
  - Verify LLM prompt includes literature context
- **B (real code + real examples)**:
  - Real API calls to Semantic Scholar
  - Generate analysis in a real field (e.g., survival analysis)
  - Verify generated code mentions appropriate methods from literature
- **C (real-world / production-like)**:
  - Full article with Introduction, Methods, Results, References
  - PDF export with proper bibliography formatting
  - Verify all DOIs are valid and papers exist

## Acceptance Criteria (must be fully satisfied)
- [ ] User can specify research field and keywords for a notebook
- [ ] System retrieves relevant papers from Semantic Scholar
- [ ] LLM prompts include literature context
- [ ] PDF export includes a References section
- [ ] All cited papers have verifiable DOIs
- [ ] Introduction can be generated based on literature

## Implementation Notes (fill during execution)
TBD

## Full Report (fill only when moving to completed/)
TBD
