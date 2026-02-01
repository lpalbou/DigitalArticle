# Backlog Item

## Title
Guided rerun: keep cell context, add a rerun comment (modal) to steer a partial rewrite (invalidate downstream)

## Backlog ID
0067

## Priority
- **P1 (completed)**: reduces failure rate and iteration cost by letting the user request a *targeted* change (e.g., “change plot colors”, “use method X”) without rewriting the whole prompt.

## Date / Time
2026-01-31T09:55:00 (local)

## Short Summary
Add a rerun mode where the user can provide a short “rerun comment” via a modal. The rerun comment is injected into the LLM prompt as a **delta request** (“keep what you did, but change X”). The rerun must **invalidate all downstream cells**, and the LLM must not consider downstream cells during regeneration.

## Key Goals
- Provide a UX-native mechanism to request a *partial rewrite* of the current cell result.
- Persist rerun comments (auditable provenance) and surface them to technical users.
- Ensure reruns never use downstream cell context (always invalidate below).

## Scope

### To do
- Frontend:
  - Add “Guided rerun (keep context + comment)” option to the rerun dropdown.
  - Open a modal to collect a short rerun comment (bounded length, clear warning about secrets).
  - Execute regenerate+run using the rerun comment.
  - Invalidate downstream cells (existing stale marking) when rerun succeeds.
- Backend:
  - Extend execute request schema to accept `rerun_comment`.
  - Persist the comment + metadata (timestamp, mode) in the cell (e.g., `cell.metadata`).
  - Incorporate `rerun_comment` into LLM calls:
    - code generation prompt (regenerate)
    - error-fix improvement prompt (retry loop)
  - Ensure prompt/context construction excludes downstream cells.

### NOT to do
- Do not allow rerun comments to become a hidden side-channel: they must be persisted and visible (provenance).
- Do not store secrets in rerun comments (treat as user input).
- Do not implement “undo rerun” / versioning here (future; see `0037`).

## Dependencies

### Backlog dependencies (ordering)
- Must follow:
  - [`0066_cell_rerun_context_hygiene.md`](../completed/0066_cell_rerun_context_hygiene.md)

### ADR dependencies (must comply)
- **All ADRs are mandatory**: [`docs/adr/README.md`](../../adr/README.md)
- **Primary ADR dependencies**:
  - [`ADR 0002`](../../adr/0002-ab-testing-ladder.md)
  - [`ADR 0005`](../../adr/0005-perfect-observability.md) (persist rerun comment + include in traces)
  - [`ADR 0008`](../../adr/0008-linting-and-quality-gates.md)

### Points of vigilance (during execution)
- Keep rerun comments short (avoid prompt bloat / “prompt soup”).
- Rerun comment must not override safety constraints or personas.
- Ensure downstream cells are invalidated and excluded from context building.

## References (source of truth)
- Frontend execution UI:
  - `frontend/src/components/PromptEditor.tsx`
  - `frontend/src/components/ReRunDropdown.tsx`
  - `frontend/src/components/NotebookContainer.tsx` (downstream stale marking)
- Backend execution:
  - `backend/app/models/notebook.py::CellExecuteRequest`
  - `backend/app/api/cells.py` (execute endpoint)
  - `backend/app/services/notebook_service.py::execute_cell`
  - `backend/app/services/llm_service.py`

## Proposal (initial; invites deeper thought)

### Context / constraints
Users often know the exact “delta” they want (e.g., a different color palette, a different fitting method) but don’t want to rewrite the entire prompt, nor discard the whole result.

### Design options considered (with long-term consequences)
#### Option A: Force user to edit the prompt/code (status quo)
- **Pros**: no new UI.
- **Cons / side effects**: messy prompt history; hard to audit what changed; higher user effort.
- **Long-term consequences**: lower correction success; weaker provenance.

#### Option B: Dedicated rerun-comment channel (recommended)
- **Pros**: explicit delta; auditable; better iteration UX; enables future self-correction persona enforcement.
- **Cons / side effects**: adds UI + schema complexity; requires careful bounds + visibility.
- **Long-term consequences**: higher reliability and better provenance.

### Recommended approach (current best choice)
Option B with:
- bounded rerun comment length
- persisted rerun history
- downstream invalidation + no downstream context in prompt building

### Testing plan (A/B/C)
> Follow [`docs/adr/0002-ab-testing-ladder.md`](../../adr/0002-ab-testing-ladder.md).

- **A (mock / conceptual)**:
  - Define the exact request fields + UI flow and how rerun history is stored.
- **B (real code + real examples)**:
  - Backend tests:
    - rerun comment is persisted in cell metadata
    - rerun comment influences the prompt payload passed to LLM (at least appears in prompt text)
  - Frontend quality gates:
    - `npm run lint`, `npm run build:check`
- **C (real-world / production-like)**:
  - Manual:
    - create a cell that produces a plot
    - guided rerun with comment “change color palette to …”
    - verify downstream cells become STALE and new output reflects the delta

## Acceptance Criteria (must be fully satisfied)
- UI offers “Guided rerun (keep context + comment)” and collects a comment via modal.
- Backend accepts and persists `rerun_comment` + metadata on the cell.
- Rerun does not consider downstream cells (and downstream cells become STALE).
- Lint/typecheck/tests are green:
  - `pytest`
  - `cd frontend && npm run lint`
  - `cd frontend && npm run build:check`
- Backlog is moved to `docs/backlog/completed/` with a Full Report.

## Implementation Notes (fill during execution)
### Backend
- Added `rerun_comment` to `CellExecuteRequest` and threaded it through execution:
  - Persisted to `cell.metadata["rerun_history"]` for provenance
  - Stored `execution.last_rerun_mode` and `execution.last_rerun_comment` on success
- Injected guided-rerun context into `_build_execution_context(...)` when a comment is provided:
  - `context["rerun_comment"]`
  - `context["current_cell_context"]["previous_code"]` (enables partial rewrite)
- Updated `LLMService` prompts so the rerun comment is highly visible and shows up in traces:
  - `_build_user_prompt(...)` prints a “GUIDED RERUN (PARTIAL REWRITE)” section
  - `asuggest_improvements(...)` includes the rerun comment in retry prompts

### Frontend
- Added a `GuidedRerunModal` (short comment input with bounded length and “no secrets” reminder).
- Added a new rerun dropdown option “Guided rerun (keep context + comment)” that opens the modal.
- Executed as a regenerate+run with `clean_rerun: true` to avoid downstream contamination and always invalidate below.

## Full Report (fill only when moving to completed/)
### What changed (source of truth)

- **Backend**
  - `backend/app/models/notebook.py`: add `CellExecuteRequest.rerun_comment`
  - `backend/app/services/notebook_service.py`:
    - persist `rerun_history`
    - inject `rerun_comment` + `current_cell_context.previous_code` into LLM context
    - pass rerun comment context into retry loop
  - `backend/app/services/llm_service.py`:
    - make rerun delta highly visible in user prompts
    - include delta in retry prompts

- **Frontend**
  - `frontend/src/components/GuidedRerunModal.tsx`: new modal
  - `frontend/src/components/ReRunDropdown.tsx`: new menu item + callback
  - `frontend/src/components/PromptEditor.tsx`: open modal + execute guided rerun
  - `frontend/src/components/NotebookContainer.tsx`: pass `rerun_comment` to backend
  - `frontend/src/types/index.ts`: extend `CellExecuteRequest` with `rerun_comment`

### Design chosen and why
Chose a **dedicated rerun-comment channel** (Option B) because it creates an explicit, auditable “delta request” that:
- doesn’t require rewriting the original prompt
- strongly steers the LLM toward minimal edits
- can later be integrated into perfect observability (`ADR 0005`) and logic self-correction (`0009`)

### A/B/C test evidence
- **A (mock / conceptual)**:
  - Defined API contract: `rerun_comment` added to `CellExecuteRequest`
  - Defined UX: dropdown → modal → regenerate+execute with delta

- **B (real code + real examples)**:
  - Backend: `pytest` (added `tests/execution/test_guided_rerun_comment.py`)
  - Frontend: `npm run lint` and `npm run build:check`

- **C (real-world / production-like)**:
  - Manual recipe (recommended):
    - Run `da-backend` + `da-frontend`
    - Create a cell that produces a plot
    - Use “Guided rerun (keep context + comment)” with a comment like “change palette, add labels”
    - Verify the output changes as requested and downstream cells become STALE

### Risks / follow-ups
- **Prompt bloat**: rerun comments are bounded in UI; we may also want an API-side max length (future hardening).
- **Observability**: full provenance of reruns is stored in metadata and should be elevated into the persistent trace store when `0007` is implemented.

## Ultimate step (MANDATORY): run recurrent tasks before declaring “done”
Before you declare the backlog item done, you MUST check [`docs/backlog/recurrent/`](../recurrent/) and execute any tasks whose triggers apply.

