# Backlog Item Template

> **CRITICAL:** Anyone executing a backlog item MUST comply with **all ADRs** in [`docs/adr/README.md`](../adr/README.md).  
> If a backlog item requires a new decision, add/update an ADR **before** implementing.
>
> **File naming (enforced):** `{BACKLOG_ID}_{short_task_description}.md` (snake_case). Example: `0003_fix_test_suite_regressions.md`  
> **Where to place it:** use `docs/backlog/proposed/` when uncertain / needs review; use `docs/backlog/planned/` when ready to execute; use `docs/backlog/recurrent/` for trigger-based recurrent tasks.

## Title
<!-- Short, specific, outcome-oriented. -->

## Backlog ID
<!-- Must match the file name prefix. Example: 0003 -->

## Priority
<!-- P0 (must do first) | P1 (next) | P2 (later). Include 1–2 bullets why. -->

## Date / Time
<!-- ISO 8601 recommended. Example: 2026-01-31T07:45:00 (local) -->

## Short Summary
<!-- 2–5 sentences describing the problem and the intended outcome. -->

## Key Goals
- <!-- Goal 1 -->
- <!-- Goal 2 -->
- <!-- Goal 3 -->

## Scope

### To do
- <!-- In-scope work item -->
- <!-- In-scope work item -->

### NOT to do
- <!-- Explicit non-goal to avoid scope creep -->
- <!-- Explicit non-goal -->

## Dependencies

### Backlog dependencies (ordering)
<!-- List other backlog items that must be completed first. Use links. -->
- **None**
  - <!-- Example: - [0003_fix_test_suite_regressions.md](planned/0003_fix_test_suite_regressions.md) -->

### ADR dependencies (must comply)
<!-- List ADRs that directly constrain this work. Use links. -->
- **All ADRs are mandatory**: [`docs/adr/README.md`](../adr/README.md)
- **Primary ADR dependencies**:
  - <!-- Example: - [ADR 0003](../adr/0003-truncation-compaction.md) -->

### Points of vigilance (during execution)
<!-- Non-negotiable things to watch for while implementing. -->
- <!-- Example: No truncation in ingest/query; if compaction is needed for rendering, log INFO and add #COMPACTION_NOTICE -->

## Recurrence (optional; only if this is a recurrent mechanism)
<!-- If recurrent, explicitly define WHEN it triggers, WHY, and the expected outcomes. -->
- **Recurrent**: No
- **Trigger**:
- **Why**:
- **Expected outcomes**:

## References (source of truth)
<!-- Link the key code/docs that define “truth” for this backlog. Keep this short and high-signal. -->
- <!-- Example: - `backend/app/services/notebook_service.py::execute_cell` -->
- <!-- Example: - `frontend/src/services/api.ts` -->

## Proposal (initial; invites deeper thought)

### Context / constraints
<!-- What must remain true? What is “source of truth” (code/docs)? -->

### Design options considered (with long-term consequences)
#### Option A
- **Pros**:
- **Cons / side effects**:
- **Long-term consequences**:

#### Option B
- **Pros**:
- **Cons / side effects**:
- **Long-term consequences**:

#### Option C (optional)
- **Pros**:
- **Cons / side effects**:
- **Long-term consequences**:

### Recommended approach (current best choice)
<!-- The choice we believe is best, and why. -->

### Testing plan (A/B/C)
> Follow the project’s testing ADR: [`docs/adr/0002-ab-testing-ladder.md`](../adr/0002-ab-testing-ladder.md).

- **A (mock / conceptual)**:
  - <!-- What will be validated with mockups or minimal scaffolding? -->
- **B (real code + real examples)**:
  - <!-- What will be validated with real code paths and concrete examples? -->
- **C (real-world / production-like)**:
  - <!-- What will be validated with realistic usage and data? If not possible, explain why. -->

## Acceptance Criteria (must be fully satisfied)
- <!-- Clear, testable criterion -->
- <!-- Clear, testable criterion -->
- <!-- Clear, testable criterion -->

## Implementation Notes (fill during execution)
<!-- Optional: links to PRs, files, screenshots, logs, benchmarks. -->

## Full Report (fill only when moving to completed/)
<!-- Required when the item is moved to docs/backlog/completed/. -->

### What changed (files/functions)

### Design chosen and why

### A/B/C test evidence

### ADR compliance notes
<!-- Explicitly call out how ADR constraints were satisfied (especially ADR 0003 and ADR 0005). -->

### Risks and follow-ups

## Ultimate step (MANDATORY): run recurrent tasks before declaring “done”

Before you declare the backlog item done, you MUST check [`docs/backlog/recurrent/`](recurrent/) and execute any tasks whose triggers apply.

- **Minimum requirement**: run the documentation sync recurrent task:
  - [`docs/backlog/recurrent/0011_documentation_sync_after_backlog_completion.md`](recurrent/0011_documentation_sync_after_backlog_completion.md)
  - (includes running: [`tools/validate_markdown_links.py`](../../tools/validate_markdown_links.py))

