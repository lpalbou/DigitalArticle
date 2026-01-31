# Backlog Item

## Title
Split Save button: left click saves, right chevron opens options

## Backlog ID
0075

## Priority
- **P1**: fixes a UX mismatch; “Save” should save immediately while keeping advanced actions behind the dropdown.

## Date / Time
2026-01-31T17:20:00 (local)

## Short Summary
The top-right Save button opened the dropdown no matter where you clicked. This change turns it into a split button: clicking the main “Save” area saves the article; clicking the right chevron opens the menu with export options.

## Key Goals
- Make “Save” do the obvious default action.
- Preserve access to export actions via the dropdown.
- Keep the change minimal and pass frontend quality gates.

## Scope

### To do
- Convert the Save button into a split button in `frontend/src/components/Header.tsx`.
- Ensure:
  - left button triggers `onSaveNotebook`
  - right chevron toggles dropdown
  - dropdown actions still work and close the menu
- Run `npm run lint` and `npm run build:check`.

### NOT to do
- Do not redesign the header layout or change export behaviors.
- Do not change backend save/export semantics.

## Dependencies

### Backlog dependencies (ordering)
- **None**

### ADR dependencies (must comply)
- **All ADRs are mandatory**: [`docs/adr/README.md`](../../adr/README.md)
- **Primary ADR dependencies**:
  - [`ADR 0002`](../../adr/0002-ab-testing-ladder.md)
  - [`ADR 0008`](../../adr/0008-linting-and-quality-gates.md)

### Points of vigilance (during execution)
- Avoid accidental click bubbling (Save shouldn’t open the dropdown).
- Keep keyboard accessibility and focus states reasonable.

## References (source of truth)
- `frontend/src/components/Header.tsx`

## Proposal (initial; invites deeper thought)

### Context / constraints
Users expect “Save” to save immediately; the dropdown should be a secondary affordance.

### Design options considered (with long-term consequences)
#### Option A: Keep single button toggling dropdown
- **Pros**: no code change.
- **Cons / side effects**: confusing; increases misclicks; slows common workflow.
- **Long-term consequences**: persistent UX friction.

#### Option B: Split button (recommended)
- **Pros**: matches user expectations; keeps advanced actions accessible.
- **Cons / side effects**: slightly more code; must be careful with focus/click targets.
- **Long-term consequences**: consistent, scalable toolbar pattern (already used for Review).

### Recommended approach (current best choice)
Option B.

### Testing plan (A/B/C)
> Follow the project’s testing ADR: [`docs/adr/0002-ab-testing-ladder.md`](../../adr/0002-ab-testing-ladder.md).

- **A (mock / conceptual)**:
  - verify click targets and behavior in code review
- **B (real code + real examples)**:
  - run `cd frontend && npm run lint`
  - run `cd frontend && npm run build:check`
- **C (real-world / production-like)**:
  - run `da-frontend`, click Save (left) vs chevron (right) and confirm behavior

## Acceptance Criteria (must be fully satisfied)
- Clicking the left “Save” area calls `onSaveNotebook` and does not open the dropdown.
- Clicking the chevron opens/closes the dropdown.
- Dropdown actions still work and close the menu.
- `npm run lint` and `npm run build:check` pass.
- Backlog moved to `docs/backlog/completed/` with a Full Report.

## Implementation Notes
- The existing “Review” split-button pattern in `Header.tsx` was reused to keep the toolbar consistent.

## Full Report

### What changed (files/functions)
- `frontend/src/components/Header.tsx`
  - Converted “Save” into a split button:
    - left segment calls `onSaveNotebook` directly
    - right chevron toggles the dropdown

### Design chosen and why
Chose **Option B** because it matches user expectations: the most frequent action (“Save”) is one click, while less frequent actions remain in the dropdown.

### A/B/C test evidence
- **A (conceptual)**:
  - Verified event flow: Save click no longer toggles `showExportDropdown`; only chevron does.
- **B (quality gates)**:
  - `cd frontend && npm run lint` ✅
  - `cd frontend && npm run build:check` ✅
  - `python tools/validate_markdown_links.py` ✅ (backlog index)
- **C (real-world)**:
  - Manual check steps:
    - run `da-frontend`
    - click left “Save” → article saves (no dropdown)
    - click chevron → menu opens with export options

### ADR compliance notes
- **ADR 0008**: frontend lint/typecheck gates were run before completion.
- **ADR 0002**: A/B done; C is a quick manual UI check.

### Risks and follow-ups
- None (small UI-only change).

## Ultimate step (MANDATORY): run recurrent tasks before declaring “done”
- Ran lint/typecheck gates (frontend) and doc link validation.

