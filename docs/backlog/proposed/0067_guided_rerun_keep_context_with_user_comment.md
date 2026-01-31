# Backlog Item

## Title
Guided rerun: keep execution context but let user add a rerun comment (modal) to steer results

## Backlog ID
0067

## Priority
- **P1 (proposed)**: reduces failure rate by giving the user a structured way to add missing constraints/context without rewriting the whole prompt.

## Date / Time
2026-01-31T09:55:00 (local)

## Short Summary
Add a rerun mode where the notebook execution context is preserved, but the user can add a short “rerun comment” (via a modal) that is injected into the LLM context/prompt for the rerun. This supports iterative refinement (“keep what worked, but add one missing constraint”) and should improve correction success.

## Key Goals
- Provide a UX-native mechanism to add corrective guidance without rewriting the cell prompt.
- Increase correction success rate by making constraints explicit (data columns, persona requirements, methodology constraints).
- Record rerun comment and its impact in traces/metadata for transparency.

## Scope

### To do
- Add a new rerun flow in the UI:
  - modal collects “rerun comment”
  - user chooses rerun mode: keep context (and optionally clean rerun; see `0066`)
- Extend backend execute endpoint to accept `rerun_comment` and `rerun_mode`.
- Incorporate `rerun_comment` into:
  - code generation prompt (if regenerating)
  - error-fix improvement prompt (if correcting)
  - logic self-correction prompt (if applicable)
- Persist the comment + rerun metadata (who/when/why) and store in traces.

### NOT to do
- Do not allow rerun comments to become a hidden “side channel”: always show them in UI and persist them.
- Do not store secrets in rerun comments (must be treated like user input).

## Dependencies

### Backlog dependencies (ordering)
- Should follow:
  - [`0003_fix_test_suite_regressions.md`](../planned/0003_fix_test_suite_regressions.md)
  - [`0066_cell_rerun_context_hygiene.md`](0066_cell_rerun_context_hygiene.md) (defines rerun modes clean vs keep)
- Strongly related to:
  - [`0007_perfect_observability_llm_agentic_tracing.md`](../planned/0007_perfect_observability_llm_agentic_tracing.md)
  - [`0009_logic_self_correction_loop.md`](../planned/0009_logic_self_correction_loop.md)

### ADR dependencies (must comply)
- **All ADRs are mandatory**: [`docs/adr/README.md`](../../adr/README.md)
- **Primary ADR dependencies**:
  - [`ADR 0001`](../../adr/0001-article-first-mixed-audience.md)
  - [`ADR 0002`](../../adr/0002-ab-testing-ladder.md)
  - [`ADR 0005`](../../adr/0005-perfect-observability.md) (store rerun comment + prompt deltas)

### Points of vigilance (during execution)
- Rerun comments must be shown to technical users (and persisted) to preserve trust.
- Guardrail: rerun comment should be short and structured (avoid “prompt soup”).
- Ensure persona constraints are still enforced; rerun comment cannot override safety constraints.

## References (source of truth)
- `frontend/src/components/*` (cell execution UI)
- `frontend/src/services/api.ts` (execute request schema)
- `backend/app/api/cells.py` (execute endpoint)
- `backend/app/services/notebook_service.py::execute_cell` (prompt building + retries)

## Proposal (initial; invites deeper thought)

### Context / constraints
- Users often know what went wrong (“use lmfit”, “use these columns”, “reset seed”) but the system has no structured place to provide that without editing prompts/code manually.

### Design options considered (with long-term consequences)
#### Option A: Force user to edit the prompt (status quo)
- **Pros**: simple; no new UI
- **Cons / side effects**: encourages messy prompt history; hard to audit what changed
- **Long-term consequences**: lower correction success; worse provenance

#### Option B: Add a dedicated rerun comment channel (recommended)
- **Pros**: explicit deltas; auditable; can be fed into self-correction logic
- **Cons / side effects**: adds UI complexity; needs careful UX to avoid confusion
- **Long-term consequences**: better iterative refinement and traceability

### Recommended approach (current best choice)
Option B with strict visibility + trace capture, and a bounded comment size to prevent prompt bloat.

### Testing plan (A/B/C)
> Follow [`docs/adr/0002-ab-testing-ladder.md`](../../adr/0002-ab-testing-ladder.md).

- **A (mock / conceptual)**:
  - mock UI flow and define how rerun comments are stored and displayed
- **B (real code + real examples)**:
  - add backend tests verifying rerun comment is persisted and changes the prompt payload
- **C (real-world / production-like)**:
  - run a notebook scenario where a rerun comment corrects a domain constraint and confirm improved success rate

## Acceptance Criteria (must be fully satisfied)
- UI offers “guided rerun (keep context)” with a rerun comment modal.
- Backend accepts and persists `rerun_comment` and `rerun_mode`.
- Traces include rerun comment and prompt deltas.

## Implementation Notes (fill during execution)
TBD

## Full Report (fill only when moving to completed/)
TBD

