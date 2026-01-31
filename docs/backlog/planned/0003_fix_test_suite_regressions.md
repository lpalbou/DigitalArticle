# Backlog Item

## Title
Restore green test suite (error analyzer + retry context + semantic async + stdout table parsing)

## Backlog ID
0003

## Priority
- **P0**: this restores the “trust baseline” for all future work (we can’t safely evolve architecture on failing primitives).

## Date / Time
2026-01-31T07:45:00 (local)

## Short Summary
The current pytest run shows multiple failures (ErrorAnalyzer classification/context passing, semantic caching returning coroutines, stdout DataFrame parsing returning no tables). Fix these regressions and restore a clean, passing test baseline.

## Key Goals
- Make `pytest` green to restore confidence and enable safe iteration.
- Ensure error analysis correctly distinguishes column errors vs index/value errors and includes context when provided.
- Fix semantic extraction caching/async behavior to return concrete results (not coroutines).
- Restore stdout table parsing behavior or update tests and implementation coherently.

## Scope

### To do
- Investigate and fix failing tests:
  - `tests/error_analyzer/test_pandas_errors.py`
  - `tests/retry_context/test_retry_context_passing.py`
  - `tests/semantic/test_knowledge_graph_caching.py`
  - `tests/semantic/test_llm_semantic_extraction.py`
  - `tests/table_parsing/test_pandas_stdout_parser.py`
- Update implementation and/or tests to match the intended behavior (favor implementation correctness).

### NOT to do
- Do not change user-visible behavior without documenting it (and adding ADR if it’s an architectural decision).
- Do not introduce truncation in ingest/query paths (ADR 0003).

## Dependencies

### Backlog dependencies (ordering)
- **None** (this is a prerequisite baseline for many other items)

### ADR dependencies (must comply)
- **All ADRs are mandatory**: [`docs/adr/README.md`](../../adr/README.md)
- **Primary ADR dependencies**:
  - [`ADR 0002`](../../adr/0002-ab-testing-ladder.md) (A/B/C test evidence)
  - [`ADR 0003`](../../adr/0003-truncation-compaction.md) (no ingest/query truncation)
  - [`ADR 0005`](../../adr/0005-perfect-observability.md) (when touching tracing/telemetry paths, ensure auditability)

### Points of vigilance (during execution)
- Do not “fix tests” by weakening correctness: prefer fixing implementation semantics.
- Avoid introducing silent truncation/compaction in any ingest/query path while resolving failures.
- Preserve trace integrity when modifying LLM/semantic/export flows (observability expectation).

## References (source of truth)
- `tests/error_analyzer/test_pandas_errors.py`
- `tests/retry_context/test_retry_context_passing.py`
- `tests/semantic/test_knowledge_graph_caching.py`
- `tests/semantic/test_llm_semantic_extraction.py`
- `tests/table_parsing/test_pandas_stdout_parser.py`

## Proposal (initial; invites deeper thought)

### Context / constraints
- Current failures indicate either regressions or mismatched expectations.
- These components are “trust primitives” (error handling, semantic export correctness, output capture).

### Design options considered (with long-term consequences)
#### Option A: Patch tests to match current outputs
- **Pros**: fastest
- **Cons / side effects**: may lock in regressions; hides correctness issues
- **Long-term consequences**: unstable behavior; user trust erosion

#### Option B: Fix implementation to satisfy intended semantics (preferred)
- **Pros**: preserves correctness; restores “source of truth”
- **Cons / side effects**: may require deeper refactor; requires careful regression coverage
- **Long-term consequences**: stable platform for future work

### Recommended approach (current best choice)
Fix implementation with minimal, targeted changes; adjust tests only when they encode incorrect expectations.

### Testing plan (A/B/C)
> Follow the project’s testing ADR: `docs/adr/0002-ab-testing-ladder.md`.

- **A (mock / conceptual)**:
  - Write small reproductions for each failure category (pandas KeyError, semantic cache path, stdout parsing cases).
- **B (real code + real examples)**:
  - Run full `pytest` locally and in CI-like environment.
  - Add/adjust tests to cover fixed edge cases.
- **C (real-world / production-like)**:
  - Execute a realistic notebook with uploaded CSV/Excel and verify:
    - stdout tables are parsed
    - semantic export endpoints work (stream and non-stream)
    - retries show correct error analyzer guidance

## Acceptance Criteria (must be fully satisfied)
- `pytest` passes fully.
- ErrorAnalyzer produces correct guidance for pandas column vs index/value errors.
- Semantic extraction cache path returns concrete graphs (no coroutine leaks).
- Stdout table parsing returns expected tables with correct attribution.

## Implementation Notes (fill during execution)
TBD

## Full Report (fill only when moving to completed/)
TBD

