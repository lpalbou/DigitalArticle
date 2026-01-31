# Backlog Item

## Title
Enforce truncation/compaction policy across codebase (markers + INFO logs + no ingest/query truncation)

## Backlog ID
0006

## Priority
- **P1**: prevents silent correctness loss and is a prerequisite for trustworthy observability and publishing.

## Date / Time
2026-01-31T07:45:00 (local)

## Short Summary
Introduce and enforce the truncation/compaction rules from ADR 0003: no truncation for data ingest/querying; truncation/compaction only for rendering or explicit user constraints, always logged at INFO, and always marked with searchable comments.

## Key Goals
- Ensure no silent truncation in ingest/query paths.
- Ensure all truncation/compaction is explicit, logged, and grep-auditable.
- Provide consistent code markers:
  - `#TRUNCATION_NOTICE: <reason>`
  - `#COMPACTION_NOTICE: <reason>`

## Scope

### To do
- Inventory existing truncation/compaction occurrences.
- Refactor to:
  - remove truncation in ingest/query
  - add markers + INFO logs where truncation/compaction remains (rendering/layout, LLM-context user-scoped)
- Add tests verifying rules.

### NOT to do
- Do not introduce truncation in ingest/query “for convenience”.
- Do not hide truncation behind generic helper functions without explicit markers/logs.

## Dependencies

### Backlog dependencies (ordering)
- Should follow: [`0003_fix_test_suite_regressions.md`](../completed/0003_fix_test_suite_regressions.md)

### ADR dependencies (must comply)
- **All ADRs are mandatory**: [`docs/adr/README.md`](../../adr/README.md)
- **Primary ADR dependencies**:
  - [`ADR 0002`](../../adr/0002-ab-testing-ladder.md)
  - [`ADR 0003`](../../adr/0003-truncation-compaction.md) (this item implements/enforces it)

### Points of vigilance (during execution)
- Do not accidentally remove necessary rendering truncation; move it behind explicit `#TRUNCATION_NOTICE` + INFO logs.
- Ensure no truncation remains in ingest/query paths (tests must guard this).
- Avoid introducing compaction without explicit markers and logs.

## References (source of truth)
- [`ADR 0003`](../../adr/0003-truncation-compaction.md)
- Grep anchors: `#TRUNCATION_NOTICE:` and `#COMPACTION_NOTICE:`

## Proposal (initial; invites deeper thought)

### Context / constraints
- LLM-context building is a frequent place where compaction may be necessary.
- Output rendering (tables, previews) is where truncation is acceptable.

### Design options considered (with long-term consequences)
#### Option A: Add markers/logs only (no behavioral changes)
- **Pros**: fast
- **Cons / side effects**: leaves correctness risk if truncation exists in ingest/query
- **Long-term consequences**: still unsafe

#### Option B: Full sweep + enforcement tests (chosen)
- **Pros**: aligns with ADR; improves trust and auditability
- **Cons / side effects**: may require performance work (pagination/streaming) instead of truncation
- **Long-term consequences**: stable correctness guarantees

### Recommended approach (current best choice)
Perform a full code sweep, remove invalid truncation, and enforce with grep-based tests and targeted unit tests.

### Testing plan (A/B/C)
> Follow `docs/adr/0002-ab-testing-ladder.md` and ADR 0003.

- **A (mock / conceptual)**:
  - Document “allowed vs forbidden” truncation examples.
- **B (real code + real examples)**:
  - Add tests that fail if `#TRUNCATION_NOTICE` / `#COMPACTION_NOTICE` usage is missing where truncation exists.
  - Add tests for key ingest/query paths (no truncation).
- **C (real-world / production-like)**:
  - Run notebooks with large datasets and confirm rendering is truncated/paginated while computations remain complete.

## Acceptance Criteria (must be fully satisfied)
- ADR 0003 is implemented and enforced in code.
- No ingest/query truncation exists.
- All remaining truncation/compaction is explicitly marked and logged at INFO.

## Implementation Notes (fill during execution)
TBD

## Full Report (fill only when moving to completed/)
TBD

