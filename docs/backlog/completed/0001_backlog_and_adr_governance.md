# Backlog Item

## Title
Introduce backlog + ADR governance system (templates, process, and initial ADR set)

## Backlog ID
0001

## Date / Time
2026-01-31T07:45:00 (local)

## Short Summary
Create a consistent backlog system under `docs/backlog/` and an ADR system under `docs/adr/` so that recommendations can be tracked, implemented safely, tested with A/B/C rigor, and reported on completion.

## Key Goals
- Provide a consistent backlog template and workflow (planned → completed + full report).
- Establish ADR storage and initial core ADRs for the project.
- Make future work auditable: designs, consequences, tests, and reports are recorded.

## Scope

### To do
- Create `docs/backlog/template.md` and `docs/backlog/README.md`.
- Create `docs/backlog/planned/` and `docs/backlog/completed/` structure.
- Create `docs/adr/README.md`, `docs/adr/template.md`, and initial ADRs.
- Ensure docs clearly explain how to use backlog and ADRs.

### NOT to do
- Do not implement the backlog items themselves (this item is only governance scaffolding).
- Do not change runtime code paths (unless needed to support documentation structure).

## Proposal (initial; invites deeper thought)

### Context / constraints
- The backlog must remain simple and lightweight, or it will be ignored.
- ADRs must not become a bureaucracy; they must capture only the decisions that matter.

### Design options considered (with long-term consequences)
#### Option A: Use GitHub Issues only
- **Pros**: already integrated, search/filter
- **Cons / side effects**: decisions drift away from code/docs; hard to enforce template/testing rigor
- **Long-term consequences**: scattered truth; hard to onboard and audit

#### Option B: Docs-native backlog + ADRs (chosen)
- **Pros**: versioned with the code; visible in repo; easy to cross-link; works offline
- **Cons / side effects**: requires light discipline to keep status current
- **Long-term consequences**: stable, navigable project memory

### Recommended approach (current best choice)
Implement `docs/backlog/` and `docs/adr/` as the canonical “work + decision” layer.

### Testing plan (A/B/C)
> Follow the project’s testing ADR: `docs/adr/0002-ab-testing-ladder.md`.

- **A (mock / conceptual)**:
  - Confirm templates contain the required fields and process docs are clear.
- **B (real code + real examples)**:
  - Create multiple real backlog items under `docs/backlog/planned/` using the template.
  - Create initial ADRs under `docs/adr/` and reference them from backlog items.
- **C (real-world / production-like)**:
  - Not applicable (process docs only). Reassess once CI automation is added.

## Acceptance Criteria (must be fully satisfied)
- `docs/backlog/template.md` includes: title, date/time, short summary, key goals, scope (to do + NOT to do), proposal (invites deeper planning), acceptance criteria.
- `docs/backlog/README.md` explains how to work with backlog and how to move items to completed with a full report.
- `docs/adr/README.md` exists and indexes the initial ADRs.
- Initial ADRs exist for:
  - A/B/C testing ladder
  - truncation/compaction policy
  - article-first mixed-audience mission
  - recursive self-correction loop (proposed)

## Implementation Notes (fill during execution)
- Implemented using only documentation changes (no runtime code changes).
- Added `docs/overview.md` links to backlog + ADR index.

## Full Report (fill only when moving to completed/)

### What changed

- **Backlog system**
  - Added `docs/backlog/template.md`
  - Added `docs/backlog/README.md`
  - Added backlog items under `docs/backlog/planned/` for the current recommendations
- **ADR system**
  - Added `docs/adr/template.md`
  - Added `docs/adr/README.md`
  - Added initial ADRs:
    - `docs/adr/0001-article-first-mixed-audience.md`
    - `docs/adr/0002-ab-testing-ladder.md`
    - `docs/adr/0003-truncation-compaction.md`
    - `docs/adr/0004-recursive-self-correction-loop.md`

### Design choice and rationale

- Chose **docs-native backlog + ADRs** to keep decisions and plans versioned with code, cross-linkable, and auditable.

### A/B/C test evidence

- **A (mock/conceptual)**: Verified templates contain required fields and the workflow is described end-to-end in `docs/backlog/README.md`.
- **B (real examples)**: Created real planned items in `docs/backlog/planned/` and real ADRs in `docs/adr/`.
- **C (real-world)**: Not applicable for governance-only work; no runtime behavior to validate.

### Risks / follow-ups

- Requires light discipline to keep `docs/backlog/planned/` current.
- Next high-priority backlog item is restoring a green test suite (`docs/backlog/planned/0003_fix_test_suite_regressions.md`).

