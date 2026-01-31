# Backlog Item (Recurrent)

## Title
Documentation sync after backlog completion (prevent documentation drift)

## Backlog ID
0011

## Priority
- **P0 (recurrent)**: this is the minimum “closure” step to keep docs truthful and navigable after changes.

## Date / Time
2026-01-31T08:40:00 (local)

## Short Summary
After completing any planned backlog item, we must update the documentation set so it reflects the current code reality. This recurrent mechanism is the primary defense against documentation drift.

## Key Goals
- Ensure docs remain truthful (“code is the source of truth”).
- Keep the documentation graph navigable (links remain valid).
- Ensure decisions remain auditable (ADRs updated when decisions changed).

## Scope

### To do
- After completing any backlog item (i.e., before finally declaring it “done”):
  - update/create/deprecate/delete relevant docs in `docs/`
  - update `README.md` if user-visible workflows or entry points changed
  - update `CHANGELOG.md` when appropriate
  - run the doc link validator:
    - [`tools/validate_markdown_links.py`](../../../tools/validate_markdown_links.py)

### NOT to do
- Do not write aspirational docs that are not grounded in code.
- Do not keep obsolete docs without clearly marking them as historical/legacy/proposal.

## Dependencies

### Backlog dependencies (ordering)
- **None** (this is triggered by other backlog items completing)

### ADR dependencies (must comply)
- **All ADRs are mandatory**: [`docs/adr/README.md`](../../adr/README.md)
- **Primary ADR dependencies**:
  - [`ADR 0002`](../../adr/0002-ab-testing-ladder.md) (A/B/C evidence discipline)
  - [`ADR 0003`](../../adr/0003-truncation-compaction.md) (docs must not normalize forbidden truncation behavior)
  - [`ADR 0005`](../../adr/0005-perfect-observability.md) (docs must accurately describe observability requirements/status)

### Points of vigilance (during execution)
- Prefer “truth banners” (historical/proposal) over deleting content that might still be useful as context.
- Never remove critical insights from `docs/knowledge_base.md`; deprecate by moving to a **DEPRECATED** section with rationale.
- Ensure any doc references are clickable and valid (run the link validator).

## Recurrence (optional; only if this is a recurrent mechanism)
- **Recurrent**: Yes
- **Trigger**: whenever any backlog item is completed (and whenever a meaningful code change lands)
- **Why**: without this, documentation drift is inevitable and undermines trust/onboarding/compliance
- **Expected outcomes**:
  - docs match the code
  - links resolve
  - ADRs reflect real decisions

## References (source of truth)
- [`docs/overview.md`](../../overview.md)
- [`docs/architecture.md`](../../architecture.md)
- [`docs/troubleshooting.md`](../../troubleshooting.md)
- [`docs/knowledge_base.md`](../../knowledge_base.md)
- [`docs/backlog/template.md`](../template.md)
- [`docs/backlog/README.md`](../README.md)

## Proposal (initial; invites deeper thought)

### Context / constraints
- Documentation drift is a recurring failure mode in fast-moving systems.
- The doc graph must be navigable and grounded in the codebase.

### Design options considered (with long-term consequences)
#### Option A: Update docs “when convenient”
- **Pros**: low friction
- **Cons / side effects**: drift becomes permanent; onboarding slows; compliance story collapses
- **Long-term consequences**: the docs lose credibility

#### Option B: Make doc sync a recurrent closure step (chosen)
- **Pros**: keeps docs accurate; creates a stable documentation graph; improves auditability
- **Cons / side effects**: requires discipline; adds small overhead per backlog completion
- **Long-term consequences**: docs become a reliable map of the system

### Recommended approach (current best choice)
Treat doc sync as a non-negotiable closure step, with link validation as a lightweight automated guardrail.

### Testing plan (A/B/C)
> Follow the project’s testing ADR: [`docs/adr/0002-ab-testing-ladder.md`](../../adr/0002-ab-testing-ladder.md).

- **A (mock / conceptual)**:
  - Identify which docs are impacted by the backlog item (list explicitly).
- **B (real code + real examples)**:
  - Update docs and run the link validator: [`tools/validate_markdown_links.py`](../../../tools/validate_markdown_links.py)
- **C (real-world / production-like)**:
  - Manual click-through of the key entry points (`README.md`, `docs/getting-started.md`, `docs/overview.md`).

## Acceptance Criteria (must be fully satisfied)
- Any docs impacted by the completed backlog item are updated (or explicitly deprecated).
- Doc links resolve (validator passes).
- ADRs are updated if the backlog changed any architectural decision (or an ADR is created first).

## Implementation Notes (fill during execution)
TBD

## Full Report (fill only when moving to completed/)
TBD

