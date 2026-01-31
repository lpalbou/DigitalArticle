# Backlog Item

## Title
Audit current dependency tree for license compliance + simplify default installs (reduce dependency footprint)

## Backlog ID
0073

## Priority
- **P1 (proposed)**: current installs pull a very large transitive dependency tree (expected, but costly); we need an auditable license report and a plan to reduce default dependency weight without losing capabilities.

## Date / Time
2026-01-31T13:15:00 (local)

## Short Summary
`pip install -e .` currently pulls a very large dependency graph (notably via `abstractcore[all]`), including heavy ML stacks. This is likely acceptable for “full feature” installs, but we should verify **license compliance** (ADR 0007) and identify opportunities to **reduce default dependencies** (split extras, make heavy features optional, avoid installing unused providers by default).

## Key Goals
- Produce a trustworthy license/compliance report for current Python + Node dependency trees.
- Identify the primary drivers of dependency bloat (e.g., “extras” that pull huge stacks).
- Propose concrete simplification actions (without breaking core functionality).

## Scope

### To do
- Run dependency + license inventory for:
  - root Python deps (`pyproject.toml`)
  - backend Python deps (`backend/pyproject.toml`)
  - frontend deps (`frontend/package.json`)
- Identify non-core heavy dependencies and why they are pulled (direct vs transitive).
- Propose a “tiered install” model:
  - minimal core (run backend + common data science libs)
  - optional extras for heavy providers / advanced features
- Create follow-up backlogs to implement changes safely (do not do large refactors inside this audit item).

### NOT to do
- Do not remove dependencies blindly; preserve features or provide explicit optional paths.
- Do not change runtime behavior without tests and a migration plan.

## Dependencies

### Backlog dependencies (ordering)
- Should follow:
  - [`0070_dependency_license_policy_and_minimize_deps.md`](0070_dependency_license_policy_and_minimize_deps.md) (or be executed alongside it if we combine efforts)

### ADR dependencies (must comply)
- **All ADRs are mandatory**: [`docs/adr/README.md`](../../adr/README.md)
- **Primary ADR dependencies**:
  - [`ADR 0002`](../../adr/0002-ab-testing-ladder.md)
  - [`ADR 0007`](../../adr/0007-permissive-licenses-and-minimal-dependencies.md)

### Points of vigilance (during execution)
- Be careful with transitive licensing: a permissive direct dependency can pull non-compliant transitive deps.
- Avoid “feature regressions by uninstall”: if we make something optional, we must document it and test both paths.
- Keep the “default install” aligned with user expectations (common analysis should work out-of-the-box).

## References (source of truth)
- [`pyproject.toml`](../../../pyproject.toml)
- [`backend/pyproject.toml`](../../../backend/pyproject.toml)
- [`frontend/package.json`](../../../frontend/package.json)
- [`docs/adr/0007-permissive-licenses-and-minimal-dependencies.md`](../../adr/0007-permissive-licenses-and-minimal-dependencies.md)

## Proposal (initial; invites deeper thought)

### Context / constraints
- Users reported a very large dependency install for Digital Article; some is expected, but we should make default installs proportionate.
- Provider support is valuable, but we don’t need to ship every provider stack in the default install.

### Design options considered (with long-term consequences)
#### Option A: Keep everything in default install (status quo)
- **Pros**: simplest UX; “everything works”.
- **Cons / side effects**: huge installs; slower CI; higher attack surface.
- **Long-term consequences**: maintenance burden and user friction.

#### Option B: Split heavy features into extras (recommended)
- **Pros**: smaller default install; users opt-in to heavy stacks; clearer governance.
- **Cons / side effects**: more documentation; more testing matrix.
- **Long-term consequences**: sustainable dependency management.

### Recommended approach (current best choice)
Option B: define a minimal default and move heavy provider stacks to optional extras, backed by clear docs and tests.

### Testing plan (A/B/C)
> Follow the project’s testing ADR: [`docs/adr/0002-ab-testing-ladder.md`](../../adr/0002-ab-testing-ladder.md).

- **A (mock / conceptual)**:
  - define which features belong to “core” vs “extras”
- **B (real code + real examples)**:
  - run install + smoke tests for core and for at least one heavy extra
- **C (real-world / production-like)**:
  - validate Docker images and real notebook flows under the split dependency model

## Acceptance Criteria (must be fully satisfied)
- We have a written license inventory report (Python + Node) and any violations are identified.
- We have a concrete proposal for reducing default dependency footprint (what moves to extras and why).
- Follow-up backlog items are created for any required code/package changes.

## Implementation Notes (fill during execution)
TBD

## Full Report (fill only when moving to completed/)
TBD

