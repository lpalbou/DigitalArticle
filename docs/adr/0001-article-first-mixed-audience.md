# ADR 0001: Article-first notebooks for mixed audiences (our “main quest”)

## ADR
ADR 0001

## Title
Article-first notebooks for both non-technical and technical experts

## Date / Time
2026-01-31T07:40:00 (local)

## Status
Accepted

## Context

Digital Article exists to help **both non-technical and technical experts** explore, analyze, and create insights from data.

Traditional analytical notebooks (Jupyter/RStudio) are powerful but “code-first”: the narrative often becomes secondary, and results are difficult to consume by non-technical stakeholders.

Digital Article also exists to fill the gap between:

- “I have done the analysis”
- “I need to write an article and publish it”

In Digital Article, doing the analysis is also **writing the article at the same time**, reducing the friction of producing a publication-ready artifact.

We require a structure that tightly couples:

- **Intent** (prompt)
- **How** (code)
- **What** (results)
- **Communication** (methodology section)

This structure also enables **semantic extraction** for searchability of:

- The article narrative
- Methodologies and results
- Skills and workflows demonstrated across notebooks

## Decision

Digital Article is designed as an **article-first** notebook with a stable cell structure:

- Prompt (intent)
- Generated/edited code (how)
- Executed results (what)
- Scientific methodology explanation (communication)

This structure must remain readable and useful to both:

- non-technical users (narrative + results are primary)
- technical users (code is always available, inspectable, editable)

## Options considered (with consequences)

### Option A: Code-first notebook with optional narrative
- **Pros**: familiar, low UX risk for engineers
- **Cons / side effects**: non-technical users remain second-class; narratives drift; semantic extraction becomes brittle
- **Long-term consequences**: product becomes “yet another notebook UI”

### Option B: Article-first with code as a derived, inspectable artifact (chosen)
- **Pros**: aligns with mission; improves readability; supports semantic exports; supports trust via transparency
- **Cons / side effects**: UX and architecture must preserve narrative integrity; code generation must be observable and correctable
- **Long-term consequences**: requires investment in error recovery + self-correction and strong export semantics

### Option C: Split products (one for narrative, one for engineers)
- **Pros**: simpler per-audience UX
- **Cons / side effects**: two products, duplication, broken collaboration
- **Long-term consequences**: fragmented roadmap and inconsistent storage formats

## Implications

- UI must support progressive disclosure (show code when needed).
- Backend must support reproducible execution and clear persistence.
- Semantics/export layers should leverage the stable structure.
- Publication should be a first-class outcome:
  - immutable “published releases” with citation/provenance (see [`ADR 0006`](0006-publish-immutable-releases-doi-lineage.md))
- Responsible AI requires strong observability of LLM/agentic steps (see [`ADR 0005`](0005-perfect-observability.md)).

## Testing strategy (A/B/C)

Follow ADR 0002. For this mission-level ADR:

- **A**: UI/UX mock flows reviewed against intent↔how↔what↔communication
- **B**: Real notebook examples demonstrate all four facets are preserved
- **C**: Real-world user workflows confirm both technical and non-technical success metrics

## Follow-ups

- Backlog item: implement recursive self-correction loop (ADR 0004)
- Backlog item: strengthen semantic exports and searchability
- Backlog item: implement immutable published releases + DOI + lineage (ADR 0006)
- Backlog item: implement perfect observability and trace store (ADR 0005)

