# ADR 0008: Linting and Quality Gates (mandatory per backlog completion)

## ADR
ADR 0008

## Title
Adopt mandatory linting + typechecking gates (backend + frontend) and enforce them via recurrent backlog checks

## Date / Time
2026-01-31T16:05:00 (local)

## Status
Accepted

## Context

Digital Article is a multi-surface system (Python backend + TypeScript/React frontend + Docker orchestration). We recently observed a large accumulation of lint and typecheck issues on the frontend, which created legitimate concern about code health and regressions.

Without explicit “quality gates”, lint and type errors tend to re-accumulate silently. This causes:

- **False confidence**: changes appear “done” but are not safe to integrate.
- **Higher failure rates**: small inconsistencies propagate into runtime errors (especially in UI state management).
- **Wasted LLM/agent budget**: retries happen due to mechanical issues that tooling would catch deterministically.
- **Documentation drift**: if we can’t keep tests/lints green, docs become less reliable as a source of truth.

We already have runtime-oriented quality mechanisms for notebook execution (lint report and deterministic safe autofix pre-execution). This ADR adds governance for **repository code quality** (developer-facing lint/typecheck/test gates).

## Decision drivers

- **Correctness first**: prioritize reliably correct answers (code/results/methodology) over feature velocity.
- **Low-friction enforcement**: make the gate easy to run locally and in CI.
- **Minimal dependency surface**: do not add heavyweight tooling unless necessary (see ADR 0007).
- **Auditability**: failures and fixes should be reproducible and observable (see ADR 0005).

## Non-goals

- This ADR does not mandate a specific formatter (e.g., Prettier vs ESLint formatting) if it adds friction.
- This ADR does not define runtime sandboxing (see backlog `0010`).
- This ADR does not replace notebook-runtime linting/autofix (see completed backlogs `0026`, `0027`, `0069`).

## Decision

1. **Every backlog completion MUST satisfy repository quality gates**:
   - **Frontend**: `npm run lint` and `npm run build:check`
   - **Backend / Python**: `pytest`
   - If a gate cannot be run (environment/tooling), the backlog item MUST document why, and must not be moved to `completed/` without a mitigation plan.

2. **Lint/typecheck failures are treated as first-class defects**:
   - If introduced by the backlog work, fix them in the same backlog.
   - If pre-existing, create a follow-up backlog item (or re-scope the current one) and document it in the Full Report.

3. **Enforcement mechanism**:
   - We enforce this via a **recurrent backlog task** that must be executed as part of the backlog “Ultimate step” (see `docs/backlog/recurrent/0012_lint_and_typecheck_quality_gates.md`).

## Options considered (with consequences)

### Option A: “Run tests if you remember” (status quo)
- **Pros**: no process overhead.
- **Cons / side effects**: drift accumulates; failures show up late; encourages “ship now, fix later.”
- **Long-term consequences**: increasing instability and loss of trust.

### Option B: Mandatory gates + recurrent enforcement (recommended)
- **Pros**: deterministic feedback loop; catches mechanical issues early; predictable quality.
- **Cons / side effects**: adds a small fixed cost to each backlog completion.
- **Long-term consequences**: sustainable reliability and maintainability.

## Testing strategy (A/B/C)

Follow [`ADR 0002`](0002-ab-testing-ladder.md).

- **A (mock / conceptual)**:
  - Define the “quality gates” and what “green” means per surface (frontend/backend).
- **B (real code + real examples)**:
  - Run the gates locally on representative changes.
- **C (real-world / production-like)**:
  - Run the same gates in CI and in Docker-based dev environments.

## References (code/docs)

- Backlog template “Ultimate step”: [`docs/backlog/template.md`](../backlog/template.md)
- Recurrent lint/typecheck gate: [`docs/backlog/recurrent/0012_lint_and_typecheck_quality_gates.md`](../backlog/recurrent/0012_lint_and_typecheck_quality_gates.md)
- Frontend scripts: `frontend/package.json`
- Completed notebook-runtime lint/autofix:
  - [`docs/backlog/completed/0026_add_lint_report_to_cell_execution.md`](../backlog/completed/0026_add_lint_report_to_cell_execution.md)
  - [`docs/backlog/completed/0027_auto_fix_safe_lint_issues.md`](../backlog/completed/0027_auto_fix_safe_lint_issues.md)
  - [`docs/backlog/completed/0069_default_safe_autofix_pre_execution.md`](../backlog/completed/0069_default_safe_autofix_pre_execution.md)

## Follow-ups

- Add CI wiring for these gates (backlog `0070` is already the starting point).

