# Backlog Item

## Title
Reduce LLM “initiative”: add a scope guard so cells do *only what was asked* (minimal prompt tuning)

## Backlog ID
0076

## Priority
- **P2 (completed)**: improves correctness/UX by reducing “over-eager” extra analysis while keeping the current system architecture intact.

## Date / Time
2026-01-31T19:25:00 (local)

## Short Summary
Sometimes cell execution does “a bit too much” (extra plots, extra analysis steps, additional transformations not requested). Add a **small, targeted prompt tuning** (“scope guard”) so code generation focuses on the requested task and avoids unnecessary initiative. This should be implemented without a full prompt rewrite, preserving existing strengths (variable reuse, personas, methodology).

## Key Goals
- Make results more predictable and aligned with the user’s explicit request.
- Reduce unrequested work (extra plots, additional modeling, extra downloads/imports) that increases failure risk.
- Preserve the ability to explore when explicitly asked (“do exploratory analysis”), without disabling it globally.

## Scope

### To do
- Add a “scope guard” to code generation prompts (and optionally retry prompts) to bias the model toward:
  - minimal sufficient changes
  - no extra analyses/plots unless explicitly requested
  - ask for clarification (or produce a short “optional next steps” comment) instead of taking initiative
- Decide whether this is:
  - always-on (default behavior), or
  - a user-facing toggle (e.g., “Focused execution”) in the UI (recommended to consider).
- Add tests that assert the prompt payload includes the scope guard text.

### NOT to do
- Do not rewrite the entire system prompt architecture (keep it a small patch).
- Do not hardcode special-case behavior for specific personas or prompts.

## Dependencies

### Backlog dependencies (ordering)
- Should follow:
  - [`0067_guided_rerun_keep_context_with_user_comment.md`](../completed/0067_guided_rerun_keep_context_with_user_comment.md) (the rerun comment UX increases user control)

### ADR dependencies (must comply)
- **All ADRs are mandatory**: [`docs/adr/README.md`](../../adr/README.md)
- **Primary ADR dependencies**:
  - [`ADR 0001`](../../adr/0001-article-first-mixed-audience.md)
  - [`ADR 0002`](../../adr/0002-ab-testing-ladder.md)
  - [`ADR 0005`](../../adr/0005-perfect-observability.md) (record prompt deltas for auditability)
  - [`ADR 0008`](../../adr/0008-linting-and-quality-gates.md)

### Points of vigilance (during execution)
- Over-correcting toward minimalism can cause **under-delivery** (missing important checks). We want “do what was asked”, not “do nothing”.
- Ensure persona constraints still apply; scope guard must not weaken safety or domain best practices.
- Avoid “prompt bloat”: keep scope guard short and placed where it has strong effect (position bias).

## References (source of truth)
- `backend/app/services/llm_service.py` (prompt construction)
- `data/personas/system/*` (persona constraints)
- Frontend rerun UI (if implementing a toggle):
  - `frontend/src/components/ReRunDropdown.tsx`
  - `frontend/src/components/PromptEditor.tsx`

## Proposal (initial; invites deeper thought)

### Context / constraints
Digital Article is strongest when it produces **correct, grounded results** reliably. “Over-initiative” increases failure probability (extra imports, extra steps, larger outputs) and can confuse non-technical readers.

### Design options considered (with long-term consequences)
#### Option A: Always-on strict scope guard (simple)
- **Pros**: immediate behavior shift; no UI complexity.
- **Cons / side effects**: can under-deliver for prompts that implicitly expect exploration.
- **Long-term consequences**: may require prompt tuning to avoid becoming “too conservative”.

#### Option B: Add a user-facing toggle (recommended to consider)
- **Pros**: user controls initiative; safe default can remain exploratory-friendly or conservative.
- **Cons / side effects**: adds UI and API surface (a new flag) and needs documentation.
- **Long-term consequences**: best alignment with mixed audience and varied workflows.

#### Option C: Heuristic-based scope guard (implicit)
- **Pros**: no UI; adapts to prompt patterns.
- **Cons / side effects**: hard to reason about; can feel inconsistent; risky for trust.
- **Long-term consequences**: difficult to debug; conflicts with observability goals.

### Recommended approach (current best choice)
Start with a **short scope guard** (Option A) and quickly evolve toward **Option B** if users want explicit control.

### Testing plan (A/B/C)
> Follow [`docs/adr/0002-ab-testing-ladder.md`](../../adr/0002-ab-testing-ladder.md).

- **A (mock / conceptual)**:
  - Draft 2–3 candidate scope-guard wordings and evaluate their likely side effects (under/over delivery).
- **B (real code + real examples)**:
  - Add unit tests asserting scope guard is present in prompt payloads.
- **C (real-world / production-like)**:
  - Run a few real notebook prompts known to trigger over-initiative and compare before/after outputs.

## Acceptance Criteria (must be fully satisfied)
- Prompt payloads include a scope guard that biases toward “do only what was asked”.
- Quality gates are green:
  - `pytest`
  - `cd frontend && npm run lint`
  - `cd frontend && npm run build:check`
- If a UI toggle is added, it is documented and default behavior is explicitly stated.

## Implementation Notes (fill during execution)
### Design choice implemented
- Implemented **Option A (always-on scope guard)** as a *minimal prompt patch* (no UI toggle yet).
- Kept it short and placed immediately before `CURRENT REQUEST:` to maximize salience (position bias).

### Code changes
- `backend/app/services/llm_service.py::_build_user_prompt`:
  - Added a **SCOPE GUARD** section right before the `CURRENT REQUEST:` block.
- `backend/app/services/llm_service.py::asuggest_improvements`:
  - Added a short scope guard to the retry prompt to reduce “extra work while fixing”.

### Tests
- Added `tests/prompting/test_scope_guard_prompt.py` asserting the scope guard is present in the user prompt payload.

## Full Report (fill only when moving to completed/)
### What changed (source of truth)
- `backend/app/services/llm_service.py`
  - `_build_user_prompt(...)`: inserted an always-on **🎯 SCOPE GUARD** section immediately before `CURRENT REQUEST:`
  - `asuggest_improvements(...)`: added a short **SCOPE GUARD** to retry prompts (keeps fixes minimal)
- `tests/prompting/test_scope_guard_prompt.py`: unit test asserting the scope guard exists in prompt payloads.

### Why this is the right next step
The most common “LLM does too much” failure mode is not a missing feature; it’s the model taking initiative (extra plots/models/transforms) which increases:
- error probability (more code paths)
- token usage and latency
- cognitive load for mixed-audience reading

This change is intentionally small: **no full prompt rewrite**, just a high-salience guard at the boundary where code is generated.

### A/B/C testing evidence
- **A (mock / conceptual)**:
  - Selected **always-on** scope guard as the first iteration, keeping it short and position-biased (right before the request).
- **B (real code + real examples)**:
  - `pytest` (includes `tests/prompting/test_scope_guard_prompt.py`)
  - `cd frontend && npm run lint`
  - `cd frontend && npm run build:check`
- **C (real-world / production-like)**:
  - Manual validation (recommended):
    - prompt a cell with a simple request (e.g., “compute summary stats for column X”)
    - verify the generated code does only that (no unrequested plots/models)
    - verify that if you explicitly ask for EDA/plots, they are produced

### Risks / follow-ups
- **Under-delivery risk**: if the guard is too strict, the LLM may omit “good practice” steps.
  - Mitigation: users can explicitly request exploration, and we can evolve to a UI toggle (“Focused execution”) if needed.

