# Backlog Item

## Title
Recurrent: run lint + typecheck quality gates (backend + frontend) before moving any backlog to completed

## Backlog ID
0012

## Priority
- **P0 (recurrent)**: prevents “quality drift” and reduces regressions; mandatory to preserve trust and correctness.

## Date / Time
2026-01-31T16:10:00 (local)

## Short Summary
This is a recurrent mechanism that enforces **repository quality gates**. Before any backlog item is moved to `docs/backlog/completed/`, run the relevant lint/typecheck/test commands. If any gate fails, fix it (if introduced by the work) or create a follow-up backlog item (if pre-existing) and document the situation.

## Key Goals
- Keep the repo in a “green” state (lint + typecheck + tests).
- Catch mechanical failures early (before they reach users).
- Make quality checks part of the standard backlog completion workflow.

## Scope

### To do
- Run the following gates when the trigger applies:
  - **Frontend**:
    - `cd frontend && npm run lint`
    - `cd frontend && npm run build:check` (includes `tsc`)
  - **Backend/Python**:
    - `pytest`
- If a gate fails:
  - identify whether it is caused by the current backlog work or pre-existing
  - fix (if current) or create a follow-up backlog item (if pre-existing)
  - capture evidence (logs/commands) in the backlog Full Report

### NOT to do
- Do not move a backlog item to `completed/` if these gates are red without an explicit, documented reason and a mitigation plan.

## Dependencies

### Backlog dependencies (ordering)
- **None** (recurrent mechanism).

### ADR dependencies (must comply)
- **All ADRs are mandatory**: [`docs/adr/README.md`](../../adr/README.md)
- **Primary ADR dependencies**:
  - [`ADR 0002`](../../adr/0002-ab-testing-ladder.md)
  - [`ADR 0005`](../../adr/0005-perfect-observability.md) (capture evidence of checks)
  - [`ADR 0007`](../../adr/0007-permissive-licenses-and-minimal-dependencies.md) (avoid adding heavy tooling)
  - [`ADR 0008`](../../adr/0008-linting-and-quality-gates.md) (this mechanism implements it)

### Points of vigilance (during execution)
- Ensure commands are run from the correct repo root/subdir.
- Avoid “tooling drift”: keep the minimal set of commands that provide strong signal.
- When environment limitations prevent running a gate (e.g., missing toolchain), document it and add a backlog item to fix the environment/CI.

## Recurrence
- **Recurrent**: Yes
- **Trigger**: Before moving any item to `docs/backlog/completed/`
- **Why**: Prevent regressions and keep repo quality consistently high.
- **Expected outcomes**:
  - lint/typecheck/tests are green, or failures are documented + addressed via follow-up backlogs.

## References (source of truth)
- Frontend scripts: `frontend/package.json`
- Python tests: `tests/`
- ADR: [`docs/adr/0008-linting-and-quality-gates.md`](../../adr/0008-linting-and-quality-gates.md)

## Proposal (initial; invites deeper thought)

### Context / constraints
- The system spans multiple languages; “green” must include both frontend and backend.

### Design options considered (with long-term consequences)
#### Option A: Only run `pytest`
- **Pros**: simpler.
- **Cons / side effects**: misses frontend type issues and lint drift.
- **Long-term consequences**: UI regressions accumulate.

#### Option B: Run both backend + frontend gates (recommended)
- **Pros**: prevents both UI and backend regressions.
- **Cons / side effects**: slightly higher completion cost.
- **Long-term consequences**: stable and predictable releases.

### Recommended approach (current best choice)
Option B.

### Testing plan (A/B/C)
> Follow the project’s testing ADR: [`docs/adr/0002-ab-testing-ladder.md`](../../adr/0002-ab-testing-ladder.md).

- **A (mock / conceptual)**:
  - define the exact commands and what “pass” means
- **B (real code + real examples)**:
  - run the commands after representative changes
- **C (real-world / production-like)**:
  - wire into CI so every PR runs the same gates

## Acceptance Criteria (must be fully satisfied)
- This recurrent backlog exists and is referenced by the backlog template and backlog README.
- The commands are clearly listed and runnable.
- Backlog completion workflow explicitly requires checking this recurrent task.

## Implementation Notes (fill during execution)
N/A (recurrent mechanism)

## Full Report (fill only when moving to completed/)
N/A (recurrent mechanism stays recurrent)

