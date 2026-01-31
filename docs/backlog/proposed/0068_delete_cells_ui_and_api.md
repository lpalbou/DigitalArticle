# Backlog Item

## Title
Delete cells (UI “X” control + backend delete endpoint + persistence)

## Backlog ID
0068

## Priority
- **P2 (proposed)**: important UX capability, but lower than correctness/robustness primitives.

## Date / Time
2026-01-31T10:15:00 (local)

## Short Summary
Users need a first-class way to delete cells. Add a clear “X” button in the cell header (top-right) with confirmation, implement a backend API to delete a cell from a notebook, persist the change, and ensure downstream state (execution state, semantics cache, and UI ordering) remains consistent.

## Key Goals
- Enable users to delete a cell intentionally and safely (confirmation).
- Keep notebook state consistent after deletion (cell order, execution counts, cached semantics).
- Preserve trust: deletion must be explicit and traceable (ADR 0005).

## Scope

### To do
- Frontend:
  - Add a delete control (X icon) in the cell header.
  - Require confirmation (modal) before deletion.
  - Optimistically remove the cell from UI, with rollback on API failure.
- Backend:
  - Add an API endpoint to delete a cell (by notebook_id + cell_id).
  - Update notebook persistence so deleted cells do not reappear on reload.
  - Invalidate any caches that depend on cell list/order (semantic graphs).
- Data integrity:
  - Ensure deleting a cell updates downstream cell ordering consistently.
  - Ensure “cell state” markers (FRESH/STALE) remain meaningful after deletion.

### NOT to do
- Do not implement “undo delete” in this backlog (future enhancement).
- Do not implement multi-user collaboration conflict resolution (future scope).

## Dependencies

### Backlog dependencies (ordering)
- Should follow: [`0003_fix_test_suite_regressions.md`](../completed/0003_fix_test_suite_regressions.md)
- Related to:
  - [`0066_cell_rerun_context_hygiene.md`](../completed/0066_cell_rerun_context_hygiene.md) (invalidation semantics are adjacent)

### ADR dependencies (must comply)
- **All ADRs are mandatory**: [`docs/adr/README.md`](../../adr/README.md)
- **Primary ADR dependencies**:
  - [`ADR 0002`](../../adr/0002-ab-testing-ladder.md)
  - [`ADR 0005`](../../adr/0005-perfect-observability.md) (trace deletion events)

### Points of vigilance (during execution)
- Deleting a cell is destructive: require explicit confirmation and clear UI affordance.
- Ensure persistence is updated atomically: deletion must be reflected in the saved notebook file/state.
- Ensure semantic caches and exported graphs are invalidated on delete (to prevent stale provenance).

## References (source of truth)
- `frontend/src/components/*` (cell rendering)
- `frontend/src/services/api.ts` (API client)
- `backend/app/api/*` (routes)
- `backend/app/services/notebook_service.py` (notebook storage + cell operations)

## Proposal (initial; invites deeper thought)

### Context / constraints
- Cell deletion interacts with notebook persistence, ordering, and semantic caching.

### Design options considered (with long-term consequences)
#### Option A: Hard delete (remove cell permanently) (recommended)
- **Pros**: simplest mental model; storage shrinks; no hidden state
- **Cons / side effects**: irreversible unless we add undo/versioning later
- **Long-term consequences**: easy to maintain; pairs well with future “version control for cells” (`0037`)

#### Option B: Soft delete (mark deleted, hide in UI)
- **Pros**: enables future restore/undo without a full versioning system
- **Cons / side effects**: more persistence complexity; exports must ignore deleted cells; more drift risk
- **Long-term consequences**: can accumulate “dead” state and complicate semantics/provenance

### Recommended approach (current best choice)
Option A (hard delete) with confirmation, and record deletion events in traces for auditability.

### Testing plan (A/B/C)
> Follow [`docs/adr/0002-ab-testing-ladder.md`](../../adr/0002-ab-testing-ladder.md).

- **A (mock / conceptual)**:
  - confirm UX flow and API contract (request/response, error handling)
- **B (real code + real examples)**:
  - backend tests: create notebook with multiple cells → delete one → verify persistence and ordering
- **C (real-world / production-like)**:
  - manual test in UI: delete cells after multiple executions; reload app; confirm deleted cells stay deleted

## Acceptance Criteria (must be fully satisfied)
- UI shows an X delete control per cell and requires confirmation.
- Backend deletes the cell and persists the change (deleted cell does not return on reload).
- Deletion invalidates dependent caches (semantic graphs) to avoid stale outputs.
- Observability captures delete events (at least notebook_id + cell_id + timestamp).

## Implementation Notes (fill during execution)
TBD

## Full Report (fill only when moving to completed/)
TBD

