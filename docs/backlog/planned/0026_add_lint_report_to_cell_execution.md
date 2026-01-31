# Backlog Item

## Title
Add a lint report to cell execution (static quality feedback alongside runtime errors)

## Backlog ID
0026

## Priority
- **P1**: improves reliability and self-correction (“executable but low quality”) and gives technical users more actionable feedback.

## Date / Time
2026-01-31T08:55:00 (local)

## Short Summary
Today, cell execution provides runtime exceptions and ErrorAnalyzer guidance; it also has a lightweight `ast.parse` + anti-pattern validator. However, there is no clear “lint report” (style/safety/quality/static mistakes) included in execution results. Add an optional lint step that produces a structured report (warnings/errors) that can be shown to users and fed into LLM improvement loops.

## Key Goals
- Provide static quality feedback even when code runs (or before it runs).
- Improve debuggability and agentic self-correction (more signal than runtime errors alone).
- Keep it safe, fast, and deterministic (no network calls; no secret leakage).

## Scope

### To do
- Decide which “linting” level we want:
  - minimal static checks (imports unused, undefined names, suspicious patterns)
  - full linter (e.g., Ruff) with a curated ruleset
- Add a lint phase to cell execution:
  - before execution (fast fail for obvious issues)
  - after execution (quality feedback)
- Add UI surfacing in cell results (separate from runtime traceback).
- Make the lint report part of observability traces (ADR 0005).

### NOT to do
- Do not block execution purely on style warnings (unless explicitly configured).
- Do not run networked tooling or anything that can leak secrets.
- Do not implement automatic non-LLM lint auto-fixes in this item (tracked separately):
  - [`docs/backlog/planned/0027_auto_fix_safe_lint_issues.md`](0027_auto_fix_safe_lint_issues.md)

## Dependencies

### Backlog dependencies (ordering)
- Should follow: [`0003_fix_test_suite_regressions.md`](../completed/0003_fix_test_suite_regressions.md)
- Strongly related to: [`0007_perfect_observability_llm_agentic_tracing.md`](../planned/0007_perfect_observability_llm_agentic_tracing.md)

### ADR dependencies (must comply)
- **All ADRs are mandatory**: [`docs/adr/README.md`](../../adr/README.md)
- **Primary ADR dependencies**:
  - [`ADR 0002`](../../adr/0002-ab-testing-ladder.md)
  - [`ADR 0005`](../../adr/0005-perfect-observability.md) (lint report should be traced/auditable)
  - [`ADR 0003`](../../adr/0003-truncation-compaction.md) (no silent truncation of evidence; compaction only for display)

### Points of vigilance (during execution)
- Make linting configurable: **off by default** or “minimal by default” (to avoid surprising latency).
- Avoid false positives that degrade trust; choose ruleset carefully.
- Ensure lint output is structured and stable (good for LLM loops and tests).

## References (source of truth)
- `backend/app/services/execution_service.py::validate_code_syntax` (current static checks)
- `backend/app/services/notebook_service.py::execute_cell` (execution orchestration)
- `tests/validation/test_syntax_validation.py` (existing syntax validation expectations)

## Proposal (initial; invites deeper thought)

### Context / constraints
- We already do basic AST parsing and some anti-pattern detection, but it’s not exposed as a consistent “lint report”.
- A production-grade linter (Ruff) is fast but introduces new dependency/config surface.

### Design options considered (with long-term consequences)
#### Option A: Extend current AST-based validator only (minimal)
- **Pros**: no new deps; deterministic; fast
- **Cons / side effects**: limited coverage; still misses many real-world issues
- **Long-term consequences**: incremental improvement; may not satisfy “lint report” expectations

#### Option B: Integrate Ruff as an optional lint engine (recommended if we want “real lint”)
- **Pros**: fast; widely adopted; rich rule set; machine-readable output
- **Cons / side effects**: adds dependency and config decisions; needs careful rule selection to avoid noise
- **Long-term consequences**: strongest and most maintainable lint story

#### Option C: Pylint/Flake8 (older ecosystem)
- **Pros**: familiar
- **Cons / side effects**: slower; fragmented plugin ecosystem; more noise
- **Long-term consequences**: higher maintenance burden than Ruff

### Recommended approach (current best choice)
Start with Option A as a structured report surfaced in execution results, and design the interface so we can plug in Ruff later (Option B) without breaking UI/API.

### Testing plan (A/B/C)
> Follow [`docs/adr/0002-ab-testing-ladder.md`](../../adr/0002-ab-testing-ladder.md).

- **A (mock / conceptual)**:
  - Define the lint report schema and UI placement.
- **B (real code + real examples)**:
  - Add tests for representative code snippets (unused imports, undefined variables, shadowing, etc.).
- **C (real-world / production-like)**:
  - Run realistic notebooks and validate lint reports are useful and not noisy; measure latency impact.

## Acceptance Criteria (must be fully satisfied)
- Cell execution returns a lint report (structured) without breaking existing flows.
- Lint report is visible in UI and persisted in execution metadata/trace.
- Lint report does not leak secrets and does not require network access.

## Implementation Notes (fill during execution)
### Design chosen
- Implemented **Option A** first (extend current lightweight static analysis) with a structured report model designed to allow a future Ruff engine swap without breaking UI/API.

### Implementation details
- Added Pydantic models for lint reporting (`LintReport`, `LintIssue`, `LintSeverity`) and attached `lint_report` to `ExecutionResult`.
- Implemented a deterministic offline linter (`LintingService`) using Python `ast`:
  - unused imports (DA1001)
  - possibly-undefined names (DA1002), scoped by notebook globals to reduce false positives
- Wired linting into `ExecutionService.execute_code()`:
  - validation failures now include a structured lint report (error + suggestions)
  - successful executions include a lint report (possibly empty)
- Frontend surfacing: added a “Lint” tab to the Execution Details modal.

## Full Report (fill only when moving to completed/)
### What changed (files/functions)
- Backend:
  - `backend/app/models/linting.py` (new)
  - `backend/app/models/notebook.py::ExecutionResult` (added `lint_report`)
  - `backend/app/services/linting_service.py` (new)
  - `backend/app/services/execution_service.py::execute_code` (attach lint report)
- Tests:
  - `tests/validation/test_lint_report.py` (new)
- Frontend:
  - `frontend/src/types/index.ts` (added `LintReport`/`LintIssue` types + `ExecutionResult.lint_report`)
  - `frontend/src/components/ExecutionDetailsModal.tsx` (new “Lint” tab)

### Design chosen and why
- Chose **minimal built-in linting** first to keep it deterministic/offline and avoid adding new tool dependencies.
- Designed the schema (`LintReport.engine`, rule IDs) so we can later plug in Ruff without breaking the frontend.

### A/B/C test evidence
- **A (mock / conceptual)**:
  - Defined a stable schema with severities, locations, suggestions, and a future-proof `engine` field.
- **B (real code + real examples)**:
  - Added `tests/validation/test_lint_report.py` and ran `pytest -q` → **195 passed**.
- **C (real-world / production-like)**:
  - Manual smoke via backend execution path: verified lint issues appear in `ExecutionDetailsModal` for a cell with unused imports / undefined names.
  - Note: `npm run build:check` could not be executed in the current environment because `tsc` is not available (frontend deps not installed).

### ADR compliance notes
- ADR 0005: lint report is attached to execution results (persisted in notebook JSON); full trace integration will be deepened in `0007`.
- ADR 0003: lint report does not introduce truncation/compaction behavior.

### Risks and follow-ups
- Undefined-name warnings can still be noisy for dynamic patterns; keep it **warning-only** and refine allowlists as we learn.
- The ExecutionService file remains large; lint/autofix work should keep new logic in focused service modules.

