# Backlog Item

## Title
Automatically fix “safe” lint issues during cell execution (non-LLM autofix with transparent diffs)

## Backlog ID
0027

## Priority
- **P1 (proposed)**: reduces avoidable failures and improves code quality without additional LLM calls, but must be done carefully to avoid semantic changes.

## Date / Time
2026-01-31T09:05:00 (local)

## Short Summary
Extend the lint-report mechanism to optionally **auto-fix** a strictly limited, deterministic subset of lint issues using non-LLM code (e.g., removing unused imports, sorting imports, formatting). Auto-fixes must be configurable, transparent (diff shown), traced (ADR 0005), and must not silently change semantics.

## Key Goals
- Reduce trivial execution failures and noise by auto-fixing safe issues.
- Preserve user trust via transparency (show the exact diff and rationale).
- Keep it deterministic and local (no network calls; no secret leakage).

## Scope

### To do
- Define an “autofix contract”:
  - what issues are considered safe to auto-fix
  - what issues must be *reported only*
  - how diffs are generated and surfaced in UI/metadata
- Implement an autofix engine that is:
  - deterministic
  - bounded (time/size limits)
  - safe (rule allowlist)
- Persist:
  - original code
  - fixed code
  - diff
  - lint issues before/after
  - trace events (flow/task/step IDs)
- Add tests for representative autofix cases and “must not change” cases.

### NOT to do
- Do not auto-fix anything that can change semantics without explicit confirmation.
- Do not silently rewrite user code (must show diff + reason).
- Do not add networked tooling into the execution path.

## Dependencies

### Backlog dependencies (ordering)
- Should follow:
  - [`0003_fix_test_suite_regressions.md`](../planned/0003_fix_test_suite_regressions.md)
  - [`0026_add_lint_report_to_cell_execution.md`](0026_add_lint_report_to_cell_execution.md) (need the lint report + schema first)

### ADR dependencies (must comply)
- **All ADRs are mandatory**: [`docs/adr/README.md`](../../adr/README.md)
- **Primary ADR dependencies**:
  - [`ADR 0002`](../../adr/0002-ab-testing-ladder.md)
  - [`ADR 0005`](../../adr/0005-perfect-observability.md) (autofix must be traced and auditable)
  - [`ADR 0003`](../../adr/0003-truncation-compaction.md) (no silent truncation of evidence; compaction only for display)
  - [`ADR 0001`](../../adr/0001-article-first-mixed-audience.md) (transparency for both audiences; progressive disclosure)

### Points of vigilance (during execution)
- **Semantic safety** is the core risk: start with a strict allowlist (safe transformations only).
- Auto-fix must be **opt-in** (or at minimum clearly configurable) to avoid surprising users.
- Always store original + fixed code + diff and expose it to technical users (and via traces).

## References (source of truth)
- `backend/app/services/execution_service.py::validate_code_syntax` (existing static checks)
- `tests/validation/test_syntax_validation.py`
- [`docs/adr/0005-perfect-observability.md`](../../adr/0005-perfect-observability.md)

## Proposal (initial; invites deeper thought)

### Context / constraints
- Many lint issues are mechanical and can be fixed deterministically.
- But auto-modifying code is a trust boundary: it must be transparent, reversible, and auditable.

### Design options considered (with long-term consequences)
#### Option A: No auto-fix (report only)
- **Pros**: safest; no semantic risk
- **Cons / side effects**: leaves avoidable friction; increases LLM usage for mechanical fixes
- **Long-term consequences**: higher cost and slower iteration

#### Option B: Safe allowlisted autofix with diffs (recommended)
- **Pros**: reduces friction; deterministic; improves code quality; works offline
- **Cons / side effects**: requires careful allowlist design; still some semantic-risk edge cases
- **Long-term consequences**: strong foundation for quality without over-reliance on LLM

#### Option C: Aggressive autofix (broad linter fix set)
- **Pros**: “fix everything” feels powerful
- **Cons / side effects**: high semantic risk; surprises users; hard to audit and trust
- **Long-term consequences**: undermines credibility

### Recommended approach (current best choice)
Option B: start with a strict allowlist of safe fixes, make it configurable, and require diffs + trace capture for every rewrite.

### Testing plan (A/B/C)
> Follow [`docs/adr/0002-ab-testing-ladder.md`](../../adr/0002-ab-testing-ladder.md).

- **A (mock / conceptual)**:
  - Define the allowlist and “do not autofix” categories with examples.
- **B (real code + real examples)**:
  - Add unit tests for the autofix engine (before/after code + diff + lint report).
- **C (real-world / production-like)**:
  - Run realistic notebooks and measure:
    - reduction in execution failures
    - user trust signals (diff clarity)
    - latency overhead

## Acceptance Criteria (must be fully satisfied)
- Autofix is configurable and defaults to the safest behavior.
- Every autofix produces a stored diff and trace event.
- The allowlist prevents semantic-changing rewrites by default.
- Tests cover both “fixed” and “refused to fix” cases.

## Implementation Notes (fill during execution)
TBD

## Full Report (fill only when moving to completed/)
TBD

