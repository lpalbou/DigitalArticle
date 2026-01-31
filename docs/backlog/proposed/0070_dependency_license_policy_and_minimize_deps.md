# Backlog Item

## Title
Enforce permissive dependency licensing + minimize dependency surface (CI guardrails + reports)

## Backlog ID
0070

## Priority
- **P1 (proposed)**: reduces governance/compliance risk and dependency drift; improves auditability and long-term maintainability.

## Date / Time
2026-01-31T12:50:00 (local)

## Short Summary
We need enforceable guardrails so Digital Article does not silently drift into non-permissive or unknown licensing dependencies, and so dependency growth stays intentional. Implement automated license scanning and dependency-surface reporting for **Python** and **Node**, with a clear exception mechanism and a “minimal dependency” review checklist.

## Key Goals
- Enforce “permissive licenses only by default” for project-maintained dependencies (Python + Node).
- Make dependency growth intentional (new deps require justification and review).
- Generate auditable reports (for release governance and debugging).

## Scope

### To do
- Implement automated license scanning for:
  - root Python deps in [`pyproject.toml`](../../../pyproject.toml)
  - backend Python deps in [`backend/pyproject.toml`](../../../backend/pyproject.toml)
  - frontend deps in [`frontend/package.json`](../../../frontend/package.json)
- Define a default allowlist/denylist (per ADR 0007) and a documented exception mechanism.
- Add a CI job (or a locally runnable script) that:
  - fails on denylisted/unknown licenses by default
  - emits a human-readable report artifact
- Add developer guidance:
  - “dependency minimization checklist” (when adding a new dep, justify why)

### NOT to do
- Do not attempt to fully remove/replace existing dependencies in this backlog (audit first, then follow-up items if needed).
- Do not introduce new major deps to enforce this policy if avoidable (tooling should be minimal).

## Dependencies

### Backlog dependencies (ordering)
- **None**
- Related:
  - [`0062_governance_compliance.md`](../proposed/0062_governance_compliance.md)

### ADR dependencies (must comply)
- **All ADRs are mandatory**: [`docs/adr/README.md`](../../adr/README.md)
- **Primary ADR dependencies**:
  - [`ADR 0002`](../../adr/0002-ab-testing-ladder.md)
  - [`ADR 0007`](../../adr/0007-permissive-licenses-and-minimal-dependencies.md)

### Points of vigilance (during execution)
- Avoid false positives from “UNKNOWN” licenses by:
  - preferring tooling that inspects installed metadata reliably
  - providing an explicit, reviewable exception file
- Keep the enforcement path deterministic and locally runnable (debuggability).
- Do not accidentally block development with noisy/unstable checks (reports must be actionable).

## References (source of truth)
- [`docs/adr/0007-permissive-licenses-and-minimal-dependencies.md`](../../adr/0007-permissive-licenses-and-minimal-dependencies.md)
- [`pyproject.toml`](../../../pyproject.toml)
- [`backend/pyproject.toml`](../../../backend/pyproject.toml)
- [`frontend/package.json`](../../../frontend/package.json)

## Proposal (initial; invites deeper thought)

### Context / constraints
- License constraints must be enforced automatically, otherwise they will drift.
- “Minimal dependencies” is a design constraint; it must be part of the contribution workflow.

### Design options considered (with long-term consequences)
#### Option A: Manual audits only
- **Pros**: no tooling needed.
- **Cons / side effects**: unreliable; drifts; expensive to repeat.
- **Long-term consequences**: compliance and security regressions are likely.

#### Option B: Automated license scanning + CI enforcement (recommended)
- **Pros**: scalable; auditable; prevents drift.
- **Cons / side effects**: requires careful allowlist/exception handling.
- **Long-term consequences**: strong governance foundation.

#### Option C: Freeze dependencies aggressively (pin and avoid upgrades)
- **Pros**: reduces change risk.
- **Cons / side effects**: security patches delayed; ecosystem moves.
- **Long-term consequences**: may harm security posture and compatibility.

### Recommended approach (current best choice)
Option B: implement automated scanning and CI enforcement with a documented exception mechanism, while keeping tooling minimal.

### Testing plan (A/B/C)
> Follow the project’s testing ADR: [`docs/adr/0002-ab-testing-ladder.md`](../../adr/0002-ab-testing-ladder.md).

- **A (mock / conceptual)**:
  - Define allowlist/denylist + exception process and review it.
- **B (real code + real examples)**:
  - Implement scripts and run them against the current repo to generate reports.
- **C (real-world / production-like)**:
  - Enforce in CI and validate it blocks a known-denylisted dependency and passes on a clean set.

## Acceptance Criteria (must be fully satisfied)
- CI (or a local script) produces a license report for Python + Node dependencies.
- CI fails on denylisted or unknown licenses by default (with an explicit exception mechanism).
- Adding a new dependency requires an explicit justification section (documented workflow).

## Implementation Notes (fill during execution)
TBD

## Full Report (fill only when moving to completed/)
TBD

