# Backlog Item

## Title
Make safe deterministic auto-fix the default (pre-execution and before LLM correction loops)

## Backlog ID
0069

## Priority
- **P0**: directly reduces avoidable failures and wasted LLM retries by fixing mechanical issues deterministically before any execution/LLM-correction work.

## Date / Time
2026-01-31T11:40:00 (local)

## Short Summary
Safe deterministic autofix is now **default-on** and runs **before validation and before the first execution attempt**, so we fix “silly mistakes” without spending LLM budget. The allowlist was tightened for notebook semantics: we only remove imports when they are **provably redundant** given the current notebook globals, and we keep every rewrite transparent via `autofix_report` (before/after + diff + applied rules).

## Key Goals
- Fix “silly mistakes” deterministically without spending LLM budget.
- Apply autofix **before** execution and **before** LLM-based retries.
- Keep user trust: only safe allowlisted rewrites, always with diff + before/after.

## Scope

### To do
- Make `CellExecuteRequest.autofix` default to **true**.
- Ensure the frontend default execution path does not disable autofix implicitly.
- Tighten fixability rules:
  - do not remove “unused imports” unless provably redundant given notebook globals
- Ensure validation-stage “anti-pattern” failures are corrected by autofix when safe.

### NOT to do
- Do not expand into semantic refactors or formatting changes.
- Do not apply any rewrite that could plausibly change notebook semantics without explicit user action.

## Dependencies

### Backlog dependencies (ordering)
- Should follow:
  - [`0003_fix_test_suite_regressions.md`](../completed/0003_fix_test_suite_regressions.md)
  - [`0027_auto_fix_safe_lint_issues.md`](../completed/0027_auto_fix_safe_lint_issues.md)

### ADR dependencies (must comply)
- **All ADRs are mandatory**: [`docs/adr/README.md`](../../adr/README.md)
- **Primary ADR dependencies**:
  - [`ADR 0002`](../../adr/0002-ab-testing-ladder.md)
  - [`ADR 0005`](../../adr/0005-perfect-observability.md)

### Points of vigilance (during execution)
- Notebook semantics: “unused in this cell” ≠ “unused in the notebook”.
- Always preserve transparency: store diff + before/after + applied rules.

## References (source of truth)
- `backend/app/services/execution_service.py`
- `backend/app/services/autofix_service.py`
- `backend/app/services/linting_service.py`
- `backend/app/services/notebook_service.py::execute_cell`

## Implementation Notes
### Design chosen
- Implemented the recommended strategy: **default-on** autofix with a **strict allowlist** designed for notebook semantics.

### Key implementation details
- Default-on toggle:
  - Backend request model defaults `CellExecuteRequest.autofix = True`.
  - Frontend execution request path defaults `autofix: true` unless explicitly disabled.
- Pre-validation (pre-exec) deterministic fixes:
  - `ExecutionService.execute_code` runs pre-validation autofix before syntax validation and before execution.
  - This targets “clearly wrong” mechanical patterns that would otherwise waste retries.
- Notebook-safe allowlist tightening:
  - Built-in linter (`LintingService`) distinguishes:
    - `DA1001`: unused import (not auto-fixable in a notebook by default)
    - `DA1101`: redundant import (auto-fixable only when the binding already exists in notebook globals and matches)
  - Autofix removes only `DA1101` imports and only when the current globals binding matches the imported binding (extra safety).
- Transparency boundary:
  - Autofix is only “silent” in the sense that it doesn’t ask the user; it is always recorded via `ExecutionResult.autofix_report` when changes occur.

## Full Report
### What changed (files/functions)
- Backend:
  - `backend/app/models/notebook.py::CellExecuteRequest` (default `autofix=True`)
  - `backend/app/services/execution_service.py::execute_code` (pre-validation autofix; default-on; rewrites happen before validation/execution)
  - `backend/app/services/linting_service.py` (redundant vs unused import detection; `DA1101` fixability tightened)
  - `backend/app/services/autofix_service.py` (strict allowlist + additional binding checks)
- Frontend:
  - `frontend/src/types/index.ts` (request typing includes `autofix?: boolean`)
  - `frontend/src/components/NotebookContainer.tsx` (defaults `autofix` to true)
  - `frontend/src/components/ReRunDropdown.tsx` / `PromptEditor.tsx` (expose “without safe auto-fix” as an explicit debug action)
- Tests:
  - `tests/validation/test_autofix.py` (updated for default-on behavior)
  - `tests/validation/test_lint_report.py` (updated: fixed issues move to `autofix_report`, not remaining in `lint_report`)

### A/B/C test evidence
- **A (mock / conceptual)**:
  - Defined “safe in a notebook” constraint: never remove a first-time import just because it is unused in a single cell.
- **B (real code + real examples)**:
  - Ran `pytest -q` → **198 passed**.
- **C (real-world / production-like)**:
  - Manual flow validated:
    - redundant imports (re-importing `pandas as pd`) are removed safely
    - multi-import statements are not rewritten
    - rewrites always include `autofix_report` diff + before/after

### ADR compliance notes
- ADR 0005: every rewrite is explicit in `autofix_report` (diff + applied rules).
- ADR 0001: progressive disclosure respected (diff is available in Execution Details, not forced into the article body).

### Risks and follow-ups
- Keep the allowlist strict; only expand with clear semantics + tests.
- Consider a per-notebook or global setting once config surfaces are unified (`0004`).

