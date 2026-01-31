# Backlog Item

## Title
Publish immutable Digital Article releases (DOI + provenance + lineage + fork/derive)

## Backlog ID
0008

## Priority
- **P2**: core product bridge to publication, but depends on observability (ADR 0005) and coherent persistence/config foundations.

## Date / Time
2026-01-31T08:10:00 (local)

## Short Summary
Implement a first-class “Publish Release” feature that produces an immutable, citable Digital Article release (ideally DOI-backed), supports lineage/derivation (a release can seed a new Digital Article), and enables Q&A/extension when data is included.

## Key Goals
- Provide an immutable release artifact that can be cited and referenced.
- Capture provenance (what data, what code, what results, what model/config, what traces).
- Support derivation: a new notebook can declare `derived_from` a published release.

## Scope

### To do
- Implement ADR 0006:
  - release artifact schema and storage
  - immutability guarantees
  - citation metadata (DOI where possible)
  - lineage model (derived_from / cites)
- Define data inclusion policy and declare omissions explicitly (no silent truncation).

### NOT to do
- Do not claim reproducibility if data is not included or is not retrievable.
- Do not silently omit data or context; omissions must be explicit and audit-friendly.

## Dependencies

### Backlog dependencies (ordering)
- Should follow:
  - [`0003_fix_test_suite_regressions.md`](0003_fix_test_suite_regressions.md)
  - [`0007_perfect_observability_llm_agentic_tracing.md`](0007_perfect_observability_llm_agentic_tracing.md) (provenance/audit)
  - [`0005_unify_persistence_roots.md`](0005_unify_persistence_roots.md) (release artifact storage)

### ADR dependencies (must comply)
- **All ADRs are mandatory**: [`docs/adr/README.md`](../../adr/README.md)
- **Primary ADR dependencies**:
  - [`ADR 0001`](../../adr/0001-article-first-mixed-audience.md) (bridge to publication)
  - [`ADR 0002`](../../adr/0002-ab-testing-ladder.md)
  - [`ADR 0003`](../../adr/0003-truncation-compaction.md) (no silent omissions; explicit compaction rules)
  - [`ADR 0005`](../../adr/0005-perfect-observability.md) (provenance depends on traces)
  - [`ADR 0006`](../../adr/0006-publish-immutable-releases-doi-lineage.md) (this item implements it)

### Points of vigilance (during execution)
- Immutability must be enforceable (hashes + read-only enforcement + clear versioning).
- Never claim reproducibility if data is missing; releases must explicitly declare included/omitted artifacts.
- Citation/DOI integration must be secure (credential handling) and auditable (trace events).

## References (source of truth)
- [`ADR 0006`](../../adr/0006-publish-immutable-releases-doi-lineage.md)
- `docs/export.md`
- `docs/architecture.md` (exports + storage + semantics map)

## Proposal (initial; invites deeper thought)

### Context / constraints
- Must align with [`ADR 0006`](../../adr/0006-publish-immutable-releases-doi-lineage.md).
- Strongly coupled with observability/provenance (`ADR 0005`).

### Design options considered (with long-term consequences)
#### Option A: Manual export bundle + manual DOI publish (fast)
- **Pros**: lowest complexity; leverages existing exports
- **Cons / side effects**: inconsistent; lineage not captured; high friction
- **Long-term consequences**: publishing remains external and brittle

#### Option B: Local “release registry” + optional DOI integration (recommended)
- **Pros**: enforce immutability and lineage locally; DOI can come later; consistent schema
- **Cons / side effects**: needs storage layout + hashing + read-only enforcement
- **Long-term consequences**: solid stepping stone to full DOI integration

#### Option C: Fully integrated DOI publish pipeline (Zenodo or alternative)
- **Pros**: best UX; strongest citation story
- **Cons / side effects**: credentials and compliance; external API dependency; governance complexity
- **Long-term consequences**: turns Digital Article into a true “analysis→publish” bridge

### Recommended approach (current best choice)
Option B first (local immutable releases + lineage + hashes), then Option C for DOI integration once the artifact schema stabilizes.

### Testing plan (A/B/C)
> Follow [`docs/adr/0002-ab-testing-ladder.md`](../../adr/0002-ab-testing-ladder.md).

- **A (mock / conceptual)**:
  - define release artifact schema and lineage model; mock DOI/citation entries
- **B (real code + real examples)**:
  - create a real release from a real notebook; verify immutability and hash integrity
  - fork/derive a new notebook from the release and verify provenance links
- **C (real-world / production-like)**:
  - publish to a DOI provider (e.g., Zenodo) and validate retrieval + citation + fork workflow

## Acceptance Criteria (must be fully satisfied)
- A release is immutable once created.
- Release artifacts include explicit provenance + integrity hashes.
- Fork/derive preserves lineage in machine-readable metadata.
- DOI integration works (or is explicitly marked as deferred with clear rationale).

## Implementation Notes (fill during execution)
TBD

## Full Report (fill only when moving to completed/)
TBD

