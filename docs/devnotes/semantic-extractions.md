# Semantic Extraction System

## Overview

Digital Article implements a dual knowledge graph system to capture both the analytical process and user expertise from computational notebooks.

## Version History

### 0.1.0 (2025-11-07)

**Dual Knowledge Graph System**

Implemented two complementary knowledge graphs:

- **Analysis Flow Graph**: Tracks data lineage from raw datasets through transformations to outcomes
- **Profile Graph**: Captures user skills (technical and biomedical) and research interests

**Architecture**

- LLM-based semantic extraction with cross-cell provenance tracking
- Smart caching system (SHA256-based) to avoid redundant LLM calls
- Standard ontologies: Dublin Core, Schema.org, PROV, DCAT, SKOS, CiTO
- JSON-LD export format for interoperability

**Key Components**

1. `SemanticAnalysisService` - Generates analysis flow graphs
   - Data assets (datasets, files) with confidentiality levels (C1-C4)
   - Transformations (methods with scientific methodology)
   - Refined assets (cleaned/computed data)
   - Outcomes (findings, visualizations)
   - Complete PROV provenance relationships

2. `SemanticProfileService` - Generates user profile graphs
   - Technical skills: pandas, numpy, scikit-learn, tensorflow, etc.
   - Biomedical skills: lifelines, biopython, pydicom, nibabel
   - Domain interests: neuroscience, clinical research, biostatistics, regulatory compliance
   - Analysis categories: exploratory, statistical testing, predictive modeling

3. `LLMSemanticExtractor` - LLM-powered extraction engine
   - Context building from prompts, code, methodology, and results
   - Structured JSON parsing with error recovery
   - Cross-cell provenance tracking
   - Asset identification with consistent CURIEs

4. `SemanticExtractionService` - Lightweight per-cell metadata
   - Fast regex/AST-based extraction during execution
   - Stored in cell metadata for real-time use
   - Not used for full graph exports

**Export Consolidation**

All semantic export formats now use the same LLM-based analysis graph:
- `format=jsonld` → Analysis graph
- `format=semantic` → Analysis graph (alias)
- `format=analysis` → Analysis graph
- `format=profile` → Profile graph

Removed deprecated `_export_to_jsonld()` method (91 lines) that used old regex/AST extraction.

**Visualization**

Knowledge graph viewer with:
- Color-coded entities: Blue (data), Orange (transformations), Purple (refined), Green (outcomes)
- Color-coded relationships: PROV ontology relationships highlighted (2px thickness)
- Clean step labels ("Step 1", "Step 2") instead of full prompts
- Interactive legend explaining entity types and data flow

**Progress Feedback**

Semantic extraction modal with 4 stages:
1. Analyzing (10%) - Reading cells and preparing context
2. Extracting (50%) - LLM analyzing assets, transformations, outcomes
3. Building Graph (85%) - Creating relationships and provenance
4. Complete (100%) - Graph ready

**Caching System**

- Cache key: SHA256 hash of notebook state (cells, content, execution)
- Stored in: `notebook.metadata.semantic_cache_{graph_type}`
- Invalidation: Automatic when cells change, code executes, or content modified
- Performance: 30-60s first extraction, instant on cache hit

**Test Coverage**

- 28 tests: LLM extraction and caching (100% passing)
- 29 tests: Cell-level metadata extraction (100% passing)
- 1 test: Export consistency verification (100% passing)

Total: 58/58 tests passing

**API Endpoints**

```
GET /api/notebooks/{id}/export?format=analysis   # Analysis flow graph
GET /api/notebooks/{id}/export?format=profile    # Profile graph
GET /api/notebooks/{id}/export?format=jsonld     # Analysis graph (alias)
GET /api/notebooks/{id}/export?format=semantic   # Analysis graph (alias)
```

**Graph Structure**

Analysis Flow Graph:
```json
{
  "@context": { /* Standard ontologies */ },
  "@graph": [
    { "@id": "notebook:...", "@type": "dcterms:Text" },
    { "@id": "cell:...", "@type": "da:Cell", "rdfs:label": "Step 1" },
    { "@id": "dataset:patient_data.csv", "@type": "dcat:Dataset" },
    { "@id": "transformation:...", "@type": "da:Transformation" },
    { "@id": "refined_asset:df", "@type": "da:Refined_asset" },
    { "@id": "finding:...", "@type": "da:Finding" }
  ],
  "triples": [
    { "subject": "transformation:...", "predicate": "prov:used", "object": "dataset:..." },
    { "subject": "refined_asset:...", "predicate": "prov:wasGeneratedBy", "object": "transformation:..." },
    { "subject": "finding:...", "predicate": "prov:wasDerivedFrom", "object": "refined_asset:..." }
  ],
  "metadata": {
    "graph_type": "analysis_flow",
    "total_cells": 3,
    "total_assets": 5,
    "total_transformations": 3,
    "total_outcomes": 2,
    "asset_types": { "dcat:Dataset": 2, "da:Variable": 3 }
  }
}
```

Profile Graph:
```json
{
  "@context": { /* Standard ontologies */ },
  "@graph": [
    { "@id": "user:researcher1", "@type": "schema:Person" },
    { "@id": "skill:pandas", "@type": "schema:DefinedTerm",
      "schema:name": "Data Manipulation", "da:skillLevel": "technical" },
    { "@id": "interest:neuroscience", "@type": "skos:Concept",
      "skos:prefLabel": "Neuroscience", "da:confidence": 0.8 }
  ],
  "triples": [
    { "subject": "user:researcher1", "predicate": "schema:knowsAbout", "object": "skill:pandas" },
    { "subject": "user:researcher1", "predicate": "schema:hasInterest", "object": "interest:neuroscience" }
  ]
}
```

**Known Limitations**

- Single-user system (no multi-user knowledge aggregation)
- LLM extraction latency (30-60s first time, but cached)
- Profile graph uses rule-based extraction (future: LLM-enhanced)
- No SPARQL endpoint (graphs exported as JSON-LD files)

**Future Enhancements**

- Semantic search API for cross-notebook queries
- Knowledge graph aggregation across users
- SPARQL endpoint for complex graph queries
- Frontend graph visualization enhancements
- External ontology linking (GO, ChEBI, HPO)
- Collaborative knowledge sharing

## Technical Details

### File Structure

```
backend/app/
├── models/
│   └── semantics.py              # Core semantic data models
├── services/
│   ├── semantic_analysis_service.py   # Analysis flow graph extraction
│   ├── semantic_profile_service.py    # Profile graph extraction
│   ├── llm_semantic_extractor.py      # LLM-based extraction engine
│   └── semantic_service.py            # Lightweight per-cell extraction
└── api/
    └── notebooks.py              # Export endpoints

frontend/src/
├── components/
│   ├── SemanticExtractionModal.tsx    # Progress feedback UI
│   └── NotebookContainer.tsx          # Export/view integration
└── public/
    └── knowledge-graph-explorer.html  # Interactive graph viewer

tests/semantic/
├── test_llm_semantic_extraction.py    # LLM extraction tests (15)
├── test_knowledge_graph_caching.py    # Caching tests (13)
└── test_semantic_extraction.py        # Cell metadata tests (29)
```

### Ontologies Used

- **Dublin Core Terms** (`dcterms`) - Document metadata and structure
- **Schema.org** (`schema`) - General entities and relationships
- **PROV** (`prov`) - Provenance and data lineage (W3C standard)
- **DCAT** (`dcat`) - Dataset classification
- **SKOS** (`skos`) - Concept definitions
- **CiTO** (`cito`) - Citations and evidence
- **STATO** (`stato`) - Statistical methods ontology
- **DA** (`da`) - Digital Article custom terms (minimal)

### Entity Types

**Analysis Graph:**
- `da:Cell` - Analysis steps
- `dcat:Dataset` - Input datasets
- `da:Transformation` - Methods/operations
- `da:Refined_asset` - Intermediate data
- `da:Finding` - Outcomes/results
- `da:Visualization` - Charts and plots

**Profile Graph:**
- `schema:Person` - User/author
- `schema:DefinedTerm` - Technical skills
- `skos:Concept` - Domain interests
- `da:Dataset` - Data types used
- `da:AnalysisCategory` - Analysis types performed

### Relationship Predicates

**Provenance:**
- `prov:used` - Transformation uses dataset
- `prov:wasGeneratedBy` - Asset generated by transformation
- `prov:wasDerivedFrom` - Asset derived from source
- `prov:wasInformedBy` - Cell informed by previous cell

**Structure:**
- `dcterms:hasPart` - Notebook has cells
- `dcterms:creator` - Notebook created by user
- `schema:nextItem` - Cell execution order

**Profile:**
- `schema:knowsAbout` - User knows skill
- `schema:hasInterest` - User interested in domain
- `da:usesDataType` - Notebook uses data type
- `da:performsAnalysisType` - Notebook performs analysis

### Cache Keys

Analysis graph cache: `semantic_cache_analysis`
Profile graph cache: `semantic_cache_profile`

Cache structure:
```json
{
  "cache_key": "sha256_hash_of_notebook_state",
  "graph": { /* Complete graph */ },
  "cached_at": "2025-11-07T21:00:00"
}
```

Cache invalidation triggers:
- Cell added, removed, or reordered
- Cell prompt, code, or methodology changed
- Cell execution (new results)
- Notebook metadata changed

## Verification

Test both graphs from a notebook:

```bash
# Analysis flow graph
curl "http://localhost:8000/api/notebooks/{id}/export?format=analysis" | jq

# Profile graph
curl "http://localhost:8000/api/notebooks/{id}/export?format=profile" | jq

# Verify export consistency (jsonld = analysis)
curl "http://localhost:8000/api/notebooks/{id}/export?format=jsonld" | jq '.metadata.graph_type'
# Should return: "analysis_flow"
```

Run tests:
```bash
# All semantic tests
python -m pytest tests/semantic/ -v
# Expected: 58/58 passing

# Specific test suites
python -m pytest tests/semantic/test_llm_semantic_extraction.py -v        # 15 tests
python -m pytest tests/semantic/test_knowledge_graph_caching.py -v        # 13 tests
python -m pytest tests/semantic/test_semantic_extraction.py -v            # 29 tests
```

## References

- [W3C PROV Ontology](https://www.w3.org/TR/prov-o/)
- [DCAT Vocabulary](https://www.w3.org/TR/vocab-dcat/)
- [Dublin Core Metadata](https://www.dublincore.org/)
- [Schema.org](https://schema.org/)
- [JSON-LD Specification](https://www.w3.org/TR/json-ld/)
