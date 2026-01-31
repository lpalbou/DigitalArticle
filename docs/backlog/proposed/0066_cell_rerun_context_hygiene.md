# Backlog Item

## Title
Cell rerun context hygiene: “clean rerun on cell change” + explicit rerun modes

## Backlog ID
0066

## Priority
- **P1 (proposed)**: directly targets correctness by preventing stale/dirty state from contaminating reruns.

## Date / Time
2026-01-31T09:55:00 (local)

## Short Summary
Today, rerunning a changed cell can reuse notebook globals/state in a way that produces incorrect or misleading results. Introduce an explicit rerun model so that when a cell changes, the default rerun behavior is a **fresh start** (clean context for that cell), while still allowing an explicit “keep context” rerun mode.

## Key Goals
- Prevent “stale variable” contamination when a cell is edited and rerun.
- Make rerun semantics explicit and inspectable (what was cleared, what was preserved, and why).
- Preserve trust by making behavior deterministic and transparent.

## Scope

### To do
- Define cell change detection:
  - prompt/code/metadata changes that should invalidate prior execution state
- Define rerun modes (API + UI):
  - **Clean rerun (default when cell changed)**: executes without stale state contamination
  - **Keep context rerun (explicit)**: preserves notebook context (see `0067`)
- Implement backend state hygiene:
  - track cell-produced variables/artifacts and clear them on clean rerun
  - ensure outputs/traces reflect the rerun mode
- Add tests for:
  - “changed cell rerun” correctness
  - “clean rerun” does not reuse stale variables

### NOT to do
- Do not silently clear the entire notebook unless explicitly requested (that breaks notebook mental model).
- Do not rely on “special casing tests”; design should generalize to real notebooks.

## Dependencies

### Backlog dependencies (ordering)
- Should follow: [`0003_fix_test_suite_regressions.md`](../planned/0003_fix_test_suite_regressions.md)
- Strongly related to:
  - [`0005_unify_persistence_roots.md`](../planned/0005_unify_persistence_roots.md) (if we persist per-cell state snapshots later)
  - [`0007_perfect_observability_llm_agentic_tracing.md`](../planned/0007_perfect_observability_llm_agentic_tracing.md) (rerun modes must be auditable)

### ADR dependencies (must comply)
- **All ADRs are mandatory**: [`docs/adr/README.md`](../../adr/README.md)
- **Primary ADR dependencies**:
  - [`ADR 0001`](../../adr/0001-article-first-mixed-audience.md) (transparent, progressive disclosure)
  - [`ADR 0002`](../../adr/0002-ab-testing-ladder.md)
  - [`ADR 0005`](../../adr/0005-perfect-observability.md) (trace rerun mode + state changes)

### Points of vigilance (during execution)
- Avoid destroying useful context unintentionally; clearing must be scoped and explainable.
- Any “clean rerun” must clearly indicate what was reset (variables, imports, files context, etc.).
- Rerun mode must be recorded in traces and persisted in notebook metadata.

## References (source of truth)
- `backend/app/services/execution_service.py` (notebook globals model)
- `backend/app/services/state_persistence_service.py` (state snapshots)
- `backend/app/services/notebook_service.py::execute_cell` (rerun orchestration)

## Proposal (initial; invites deeper thought)

### Context / constraints
- The current notebook globals model is per-notebook, not per-cell.
- Correctness failures from stale state are subtle and erode trust.

### Design options considered (with long-term consequences)
#### Option A: Clear the entire notebook kernel on any cell edit (brute force)
- **Pros**: simplest correctness story
- **Cons / side effects**: destroys notebook workflow; expensive; breaks multi-cell analyses
- **Long-term consequences**: poor UX; users fight the system

#### Option B: Track per-cell “writes” and clear only what the cell produced (recommended)
- **Pros**: preserves notebook workflow; targeted hygiene; good correctness/UX balance
- **Cons / side effects**: requires tracking variable diffs and artifacts; edge cases with mutable objects
- **Long-term consequences**: scalable foundation for dependency/invalidation features

#### Option C: Re-execute from the top to the edited cell (notebook replay)
- **Pros**: matches “restart & run all to here” mental model; strongest determinism
- **Cons / side effects**: slow; needs dependency graph and deterministic execution; can re-trigger expensive operations
- **Long-term consequences**: powerful but higher complexity; better as a later feature

### Recommended approach (current best choice)
Start with Option B (per-cell write tracking + targeted clearing), and design the interface so Option C can be added later as an advanced rerun mode.

### Testing plan (A/B/C)
> Follow [`docs/adr/0002-ab-testing-ladder.md`](../../adr/0002-ab-testing-ladder.md).

- **A (mock / conceptual)**:
  - define rerun modes + state-clearing rules with examples
- **B (real code + real examples)**:
  - add tests with multi-cell notebooks where a cell is edited and rerun; verify results are not contaminated by old variables
- **C (real-world / production-like)**:
  - run realistic notebooks with uploaded data and confirm rerun behavior is predictable and explainable

## Acceptance Criteria (must be fully satisfied)
- When a cell changes and is rerun, stale variables produced by its previous version do not affect results.
- UI exposes which rerun mode was used.
- Traces/metadata record rerun mode and state-clearing actions.

## Implementation Notes (fill during execution)
TBD

## Full Report (fill only when moving to completed/)
TBD

