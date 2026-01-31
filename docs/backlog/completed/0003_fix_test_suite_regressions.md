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
### Root causes found
- **Import stability**: part of the test suite imports `backend.app.*`, but pytest was not consistently placing the repo root on `sys.path`, causing `ModuleNotFoundError` during collection.
- **ErrorAnalyzer misclassification**:
  - pandas KeyError classification treated any traceback containing `get_loc` as an index/value error, incorrectly classifying column errors (because DataFrame `__getitem__` uses `self.columns.get_loc`).
  - the “logical coherence” analyzer could mask real exception types (e.g., `KeyError`) by returning `LogicalCoherenceError` when context was present.
- **Async/sync mismatch in tests**: semantic extraction services are `async` (by design), but tests called them without awaiting, resulting in coroutine objects.
- **Stdout parsing regressions**:
  - stdout DataFrame parsing was disabled in `ExecutionService.execute_code`, breaking expectations for `print(df)` parsing.
  - single-column DataFrame stdout parsing failed because `_parse_pandas_stdout` did a global `.strip()` before splitting lines (removing indentation required to detect single-column headers).
- **Variable table capture fragility**:
  - `_capture_tables` used value-based `.equals()` to detect modifications; this misses “reassignment to a new DataFrame with identical values” and is sensitive to restored state.

## Full Report (fill only when moving to completed/)
### Summary
Restored a fully green test suite by fixing import-path stability, pandas KeyError classification, async test usage, and stdout/variable table capture behavior.

### What changed (source of truth)
- `tests/conftest.py`
  - Ensures repo root is added to `sys.path` for deterministic imports (enables `import backend.app.*`).
- `backend/app/services/error_analyzer.py`
  - **Do not mask real exceptions**: logical coherence analyzer now only runs for explicit/empty error_type flows (post-success style checks), not for concrete exceptions.
  - **Fix pandas KeyError classification**: distinguish `columns.get_loc` (column error) vs `index.get_loc` (index/value error).
- `tests/semantic/test_knowledge_graph_caching.py`
  - Use `asyncio.run(...)` to call async `extract_analysis_graph` in synchronous tests (no coroutine leaks).
- `tests/semantic/test_llm_semantic_extraction.py`
  - Use `asyncio.run(...)` to call async `extract_rich_semantics` in synchronous tests.
- `backend/app/services/execution_service.py`
  - Re-enabled parsing of pandas DataFrames from stdout (`print(df)`) into structured tables with `source='stdout'`.
  - Fixed `_parse_pandas_stdout` to preserve leading whitespace (single-column DataFrame parsing).
  - Improved `_capture_tables` to treat “DataFrame reassigned to a new object” as modified (capture even if `.equals()` is true).

### Design choices (and why)
- **Import stability via `tests/conftest.py`**:
  - This is deterministic and avoids relying on pytest import-mode quirks or per-test sys.path hacks.
- **Do not override exception types with logical checks**:
  - “Logical coherence” checks are valuable, but masking `KeyError` breaks debuggability and violates the expectation that ErrorAnalyzer enhances (not re-labels) technical errors.
- **Async test execution via `asyncio.run`**:
  - Keeps the production API async without forcing `pytest-asyncio` rewrites across the suite.
- **Stdout parsing restored**:
  - Maintains backward compatibility and enables structured capture when users print DataFrames (even if `display()` remains recommended).

### A/B/C testing evidence
- **A (mock / conceptual)**:
  - Mapped each failing test to a root cause (import path, KeyError classification, async coroutine leaks, stdout parsing disabled, single-column parsing, DataFrame reassignment).
- **B (real code + real examples)**:
  - Ran `pytest -q` → **193 passed**.
- **C (real-world / production-like)**:
  - Performed a minimal “notebook-like” run by executing representative code via `ExecutionService.execute_code` and verifying both `source='variable'` and `source='stdout'` tables are produced.

### Risks / follow-ups
- ExecutionService remains a large file; future work should continue extracting focused responsibilities (linting/autofix will add more).
- State persistence can rehydrate prior notebook state; future rerun work (`0066`) should formalize per-cell variable tracking and downstream invalidation.

