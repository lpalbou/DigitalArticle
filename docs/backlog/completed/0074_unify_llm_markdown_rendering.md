# Backlog Item

## Title
Unify user-facing LLM markdown rendering via `MarkdownRenderer` (review feedback + abstract)

## Backlog ID
0074

## Priority
- **P0**: inconsistent markdown rendering makes LLM outputs harder to read, breaks lists/code formatting, and increases “truth drift” between what the LLM intends vs what the user sees.

## Date / Time
2026-01-31T16:55:00 (local)

## Short Summary
`frontend/src/components/MarkdownRenderer.tsx` is intended to be the canonical, reusable renderer for user-facing LLM markdown. A quick audit found two user-facing LLM output surfaces still bypassing it (inline cell review feedback and the notebook abstract). This backlog unified these surfaces so markdown renders consistently.

## Key Goals
- Ensure user-facing LLM strings that may contain markdown render through `MarkdownRenderer`.
- Reduce duplicated ad-hoc rendering (`whitespace-pre-wrap`, raw `<p>`) for LLM outputs.
- Keep the change minimal, safe, and fully covered by quality gates.

## Scope

### To do
- Audit all user-facing LLM response surfaces in `frontend/src/components/`.
- Migrate any remaining “raw text” LLM rendering to `MarkdownRenderer`.
- Run quality gates (lint + typecheck/build + pytest).

### NOT to do
- Do not redesign the UI styling system or rewrite markdown CSS.
- Do not change backend review/abstract generation formats.

## Dependencies

### Backlog dependencies (ordering)
- **None**

### ADR dependencies (must comply)
- **All ADRs are mandatory**: [`docs/adr/README.md`](../../adr/README.md)
- **Primary ADR dependencies**:
  - [`ADR 0002`](../../adr/0002-ab-testing-ladder.md) (A/B/C testing ladder)
  - [`ADR 0005`](../../adr/0005-perfect-observability.md) (capture evidence of checks)
  - [`ADR 0008`](../../adr/0008-linting-and-quality-gates.md) (mandatory gates)

### Points of vigilance (during execution)
- `MarkdownRenderer` injects HTML via `dangerouslySetInnerHTML`; only use it for trusted markdown sources (our own LLM outputs and known content).
- Preserve existing UX: severity styling in review panels must remain readable.
- Do not introduce new frontend dependencies (ADR 0007).

## References (source of truth)
- `frontend/src/components/MarkdownRenderer.tsx`
- `frontend/src/components/ReviewPanel.tsx`
- `frontend/src/components/NotebookContainer.tsx` (Abstract section)
- `frontend/src/components/ArticleChatPanel.tsx` (already using `MarkdownRenderer`)
- `frontend/src/components/ArticleReviewModal.tsx` (already using `MarkdownRenderer`)

## Proposal (initial; invites deeper thought)

### Context / constraints
- LLM outputs frequently include markdown (lists, headings, code fences). Rendering them as plain text reduces usability and increases misinterpretation risk.

### Design options considered (with long-term consequences)
#### Option A: Leave as-is (raw text for some surfaces)
- **Pros**: no work.
- **Cons / side effects**: inconsistent UX; markdown often unreadable; duplicated rendering patterns.
- **Long-term consequences**: LLM outputs become less trustworthy/usable; more UI drift.

#### Option B: Use `MarkdownRenderer` for all user-facing LLM response strings (recommended)
- **Pros**: consistent rendering; code/list formatting; single place for improvements (copy buttons, highlighting).
- **Cons / side effects**: `dangerouslySetInnerHTML` requires discipline and trust boundaries.
- **Long-term consequences**: sustainable and consistent user-facing content rendering.

### Recommended approach (current best choice)
Option B.

### Testing plan (A/B/C)
> Follow the project’s testing ADR: [`docs/adr/0002-ab-testing-ladder.md`](../../adr/0002-ab-testing-ladder.md).

- **A (mock / conceptual)**:
  - static audit: identify LLM-output strings rendered without `MarkdownRenderer`
- **B (real code + real examples)**:
  - run `npm run lint` + `npm run build:check`
  - run `pytest`
- **C (real-world / production-like)**:
  - run `da-backend` + `da-frontend`, generate an abstract and a review, verify bullets/code render correctly

## Acceptance Criteria (must be fully satisfied)
- `ReviewPanel` renders `overall_assessment`, `message`, and `suggestion` via `MarkdownRenderer`.
- Notebook abstract renders via `MarkdownRenderer`.
- `npm run lint` and `npm run build:check` pass.
- `pytest` passes.
- This backlog is moved to `docs/backlog/completed/` with a Full Report including A/B/C evidence.

## Implementation Notes
- This change is intentionally minimal: we only swapped “raw text” render sites to the existing `MarkdownRenderer`.

## Full Report

### What changed (files/functions)
- **Unified review markdown rendering**:
  - `frontend/src/components/ReviewPanel.tsx`
    - `review.overall_assessment` now renders via `MarkdownRenderer`
    - `finding.message` now renders via `MarkdownRenderer`
    - `finding.suggestion` now renders via `MarkdownRenderer`
- **Unified abstract markdown rendering**:
  - `frontend/src/components/NotebookContainer.tsx`
    - Abstract section now renders via `MarkdownRenderer` instead of `whitespace-pre-wrap` text.

### Design chosen and why
Chose **Option B** (use `MarkdownRenderer`) because LLM outputs frequently include markdown and we already have a canonical renderer + CSS (`md-content`, code highlighting, code-copy).

### A/B/C test evidence
- **A (audit)**:
  - Found `ReviewPanel` and notebook Abstract rendering bypassing `MarkdownRenderer`.
  - Confirmed no other markdown libraries are used in the frontend; `MarkdownRenderer` is the sole markdown renderer.
- **B (quality gates)**:
  - `cd frontend && npm run lint` ✅
  - `cd frontend && npm run build:check` ✅
  - `pytest` ✅ (198 passed)
  - `python tools/validate_markdown_links.py` ✅
- **C (real-world)**:
  - Requires a configured working LLM provider to actually generate an abstract/review.
  - Manual verification steps:
    - Start `da-backend` and `da-frontend`
    - Generate an Abstract and a Review
    - Confirm lists/code blocks render (not as raw text) and `.md-content` styles apply.

### ADR compliance notes
- **ADR 0008**: ran lint/typecheck/test gates before completion.
- **ADR 0002**: executed A/B; C documented as a manual smoke test due to LLM/provider dependency.
- **ADR 0005**: captured command evidence in this report.

### Risks and follow-ups
- `MarkdownRenderer` uses `dangerouslySetInnerHTML`. This is acceptable for trusted internal content, but reinforces the need for execution/LLM security hardening (see backlog `0072`).

## Ultimate step (MANDATORY): run recurrent tasks before declaring “done”
- Ran recurrent lint/typecheck gates (`0012`) and doc link validation (`0011` includes `tools/validate_markdown_links.py`).

