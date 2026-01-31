# ADR 0006: Publishing immutable Digital Articles (DOI + lineage + extensions)

## ADR
ADR 0006

## Title
Publish immutable “Digital Article releases” with citation (DOI) and derivation/lineage support

## Date / Time
2026-01-31T08:05:00 (local)

## Status
Proposed

## Context

Digital Article is meant to fill the gap between:

- “I have done the analysis”
- “I need to write an article and publish it”

In Digital Article, **doing the analysis is also writing the article** (intent↔code↔results↔methodology) which reduces friction for publication.

Once “published”, the system should support an **immutable version** that others can refer to and cite (e.g., via DOI, Zenodo or a better registry if available).

Unlike conventional static articles, a published Digital Article can (when data is included/available):

- be **queried** (ask additional questions to the article)
- be **extended** with complementary analysis

This also enables a “lineage graph” where a Digital Article can become the starting point for another Digital Article (fork/derive), reusing ideas, results, and methodology with explicit provenance.

## Decision

Digital Article should support a first-class concept of a **Published Release**:

- A release is **immutable** once created.
- A release is **citable** (ideally DOI-backed).
- A release can be **forked/derived** into a new working Digital Article with explicit provenance links.

The release artifact should capture sufficient reproducibility and provenance:

- notebook export (JSON/JSON-LD/semantic graphs as applicable)
- rendered formats (PDF/HTML/Markdown) as needed for dissemination
- configuration and environment metadata (versions, model/provider used)
- optional data packaging (when policy/size permits)
- integrity hashes of artifacts
- licensing and citation metadata

## Options considered (with consequences)

### Option A: Manual export + manual DOI publish (minimal)
- **Pros**: simplest; leverages existing exports; avoids credential/security complexity
- **Cons / side effects**: inconsistent; users may forget provenance; high friction; lineage not captured
- **Long-term consequences**: “publication” remains an external, brittle workflow

### Option B: Integrated “Publish” pipeline to a DOI provider (recommended long term)
- **Pros**: consistent; reproducible; captures provenance; supports lineage; lowers friction significantly
- **Cons / side effects**: requires credentials/secrets handling; API integration; governance around data licensing
- **Long-term consequences**: product becomes a reliable bridge from analysis to publication

### Option C: Internal registry only (no DOI)
- **Pros**: easier than external DOI; can still enforce immutability + lineage
- **Cons / side effects**: weak citation story; limited interoperability
- **Long-term consequences**: not sufficient for academic/regulatory contexts

## Implications

- Requires strong provenance and traceability (see [`ADR 0005`](0005-perfect-observability.md)).
- Requires clear data inclusion policy:
  - “no truncation for ingest/query” remains true (see [`ADR 0003`](0003-truncation-compaction.md))
  - release artifacts must not silently omit data without explicit declaration
- Requires a lineage model:
  - `derived_from` links (release → new notebook)
  - citation links (release cites prior releases)

## Testing strategy (A/B/C)

Follow [`ADR 0002`](0002-ab-testing-ladder.md).

- **A**: define release artifact schema and lineage model; mock publication flows and citations.
- **B**: implement and test creation of immutable local releases (hashes, read-only behavior), and export bundles.
- **C**: publish a real release to a DOI provider (e.g., Zenodo) and validate citation + retrieval + fork workflow.

## Follow-ups

- Backlog item: implement “Publish Release” artifacts + immutability + lineage graph + DOI integration.

