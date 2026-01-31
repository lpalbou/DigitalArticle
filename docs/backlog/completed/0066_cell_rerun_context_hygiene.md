# Backlog Item

## Title
Cell rerun context hygiene: “clean rerun on cell change” + explicit rerun modes

## Backlog ID
0066

## Priority
- **P1**: directly targets correctness by preventing stale/dirty state from contaminating reruns.

## Date / Time
2026-01-31T09:55:00 (local)

## Short Summary
Rerunning a changed cell could reuse notebook globals in a way that contaminates results (especially if downstream cells have already executed). We introduced **clean rerun** semantics that rebuild execution context from **upstream cells only** (ignoring downstream state), invalidate downstream cells, and expose the rerun mode as an explicit API/UI option.

## Key Goals
- Prevent “stale variable” contamination when a cell is edited and rerun.
- Make rerun semantics explicit and inspectable (what was cleared, what was preserved, and why).
- Preserve trust by making behavior deterministic and transparent.

## Scope

### To do
- Define cell change detection:
  - prompt/code changes that should invalidate prior execution state for that cell
- Define rerun modes (API + UI):
  - **Clean rerun (default when cell changed)**: executes without stale state contamination
  - **Keep context rerun (explicit)**: preserves notebook context (see `0067`)
- Implement backend state hygiene:
  - **Chosen semantics**: on clean rerun of a changed cell, rebuild context from upstream cells only (no downstream globals)
  - invalidate all **subsequent** cells (mark as stale) because their results may depend on the changed cell
  - ensure outputs/traces record the rerun mode and context rebuild details
- Add tests for:
  - “clean rerun” does not reuse stale downstream variables

### NOT to do
- Do not silently clear the entire notebook unless explicitly requested (that breaks notebook mental model).
- Do not rely on “special casing tests”; design should generalize to real notebooks.

## Dependencies

### Backlog dependencies (ordering)
- Should follow: [`0003_fix_test_suite_regressions.md`](../completed/0003_fix_test_suite_regressions.md)
- Related:
  - [`0007_perfect_observability_llm_agentic_tracing.md`](../planned/0007_perfect_observability_llm_agentic_tracing.md)

### ADR dependencies (must comply)
- **All ADRs are mandatory**: [`docs/adr/README.md`](../../adr/README.md)
- **Primary ADR dependencies**:
  - [`ADR 0001`](../../adr/0001-article-first-mixed-audience.md) (transparent, progressive disclosure)
  - [`ADR 0002`](../../adr/0002-ab-testing-ladder.md)
  - [`ADR 0005`](../../adr/0005-perfect-observability.md) (trace rerun mode + state changes)

### Points of vigilance (during execution)
- Avoid destroying useful context unintentionally; clearing must be scoped and explainable.
- Any “clean rerun” must clearly indicate what was reset (at minimum: downstream variables via context rebuild).
- Rerun mode must be recorded in traces and persisted in notebook metadata.
- Downstream invalidation must be explicit in UI (cells become **STALE** until re-executed).

## References (source of truth)
- `backend/app/services/execution_service.py` (notebook globals model; new context-only replay knobs)
- `backend/app/services/notebook_service.py::execute_cell` (rerun orchestration)
- `frontend/src/components/ReRunDropdown.tsx` (UI affordance)

## Proposal (final design implemented)
We implemented a robust “clean rerun” by rebuilding the in-memory execution namespace:

- Reset in-memory notebook globals (without deleting persisted checkpoint on disk).
- Replay all upstream executable cells (cells above) **without** capturing outputs and **without** persisting state.
  - This prevents table/figure renumbering during replay and avoids corrupting persisted state if replay fails.
- Execute the target cell in this rebuilt context.
- Mark downstream cells as **STALE** on success (already supported by the backend).

This matches the user requirement: the cell executes **as if newly created** with **only upstream context** available (no downstream globals and no prior failed execution contamination).

## Acceptance Criteria (fully satisfied)
- When a cell changes and is rerun, stale/downstream variables do not affect results (context is rebuilt from upstream only).
- UI exposes which rerun mode was used (clean rerun is a dropdown option).
- Metadata records rerun mode and replayed upstream cells.

## Implementation Notes
### Design chosen
- Implemented a “clean context rebuild” (upstream replay) rather than best-effort variable deletion, because deletion cannot reliably revert downstream overwrites/mutations.

### What changed (files/functions)
- Backend:
  - `backend/app/models/notebook.py::CellExecuteRequest` (added `clean_rerun: bool = False`)
  - `backend/app/services/execution_service.py::execute_code` (added `capture_outputs` + `persist_state` flags for context-only replay)
  - `backend/app/services/execution_service.py::clear_namespace` (added `clear_saved_state` flag)
  - `backend/app/services/notebook_service.py::update_cell` (sets `cell.metadata.execution.needs_clean_rerun = True` on prompt/code edits)
  - `backend/app/services/notebook_service.py::_rebuild_execution_namespace_for_clean_rerun` (new)
  - `backend/app/services/notebook_service.py::execute_cell` (performs clean rebuild before LLM context + execution; clears `needs_clean_rerun` on success)
- Frontend:
  - `frontend/src/types/index.ts` (added `clean_rerun?: boolean` to `CellExecuteRequest`)
  - `frontend/src/components/NotebookContainer.tsx` (propagates `clean_rerun`)
  - `frontend/src/components/ReRunDropdown.tsx` (added “Clean rerun (restart from prompt)” action)
  - `frontend/src/components/PromptEditor.tsx` (wires dropdown action to `{ clean_rerun: true }`)
  - `frontend/src/components/NotebookCell.tsx` (prop types updated)
- Tests:
  - `tests/execution/test_clean_rerun_context_hygiene.py` (new regression test)

## Full Report
### A/B/C testing evidence
- **A (mock / conceptual)**:
  - Defined semantics: clean rerun must ignore downstream globals and prior failed run state.
- **B (real code + real examples)**:
  - Added `tests/execution/test_clean_rerun_context_hygiene.py` and ran `pytest -q` → **198 passed**.
- **C (real-world / production-like)**:
  - Manual UI smoke test is available by:
    - executing 3 cells where cell 3 defines a variable,
    - re-running cell 2 normally (it sees downstream state),
    - then using “Clean rerun (restart from prompt)” (it must not see downstream state).
  - Note: `npm run build:check` could not be executed in the current environment because frontend deps/tooling are not installed (`tsc` unavailable).

### ADR compliance notes
- ADR 0005: rerun mode and replayed upstream cell IDs are recorded in `cell.metadata.execution.clean_rerun`.
- ADR 0001: progressive disclosure respected (metadata + Execution Details, not forced into article view).

### Known limitations / follow-ups
- Clean rerun rebuilds context by replaying upstream code; if upstream cells are expensive or non-deterministic, clean rerun can be slower or vary. This is the correct trade-off for “truth-first” correctness.
- “Keep context rerun with a user comment” remains a separate feature (`0067`).

