# Backlog Item

## Title
Secure user-installed libraries (allowlisted, sandboxed “install package” workflow)

## Backlog ID
0071

## Priority
- **P1 (proposed)**: enables real-world analysis breadth (domain libraries) but is a major security boundary; must be done carefully and likely depends on sandbox hardening.

## Date / Time
2026-01-31T12:55:00 (local)

## Short Summary
Users will eventually need a way to install domain-specific libraries (Jupyter-like workflows), but in Digital Article this must be treated as a **security and governance boundary**. Design and implement a safe “install package” workflow with isolation (per notebook/user environment), allowlisting, auditing, and resource limits. This should integrate with execution (imports) and the UI in a transparent way.

## Key Goals
- Enable installing additional Python packages without rebuilding the whole deployment.
- Keep execution secure: isolation, allowlists, resource limits, and auditable install events.
- Keep user trust: explicit UI, recorded actions, and reproducible environment metadata.

## Scope

### To do
- Design a secure package installation model:
  - scope: per-notebook vs per-user vs global
  - isolation: venv vs container vs other sandbox mechanism
  - allowlist and license constraints (ADR 0007)
  - caching and reproducibility (pin versions, record metadata)
- Add backend API endpoints (or a controlled task flow) for install requests.
- Add UI affordance:
  - explicit “Install package” action + confirmation + progress
  - clear error messages when a package is blocked/not allowed
- Integrate with execution:
  - missing import detection can suggest installation, but should never auto-install silently

### NOT to do
- Do not allow arbitrary `pip install` from within code cells (too easy to exploit; breaks governance).
- Do not allow unbounded network egress or arbitrary package sources by default.

## Dependencies

### Backlog dependencies (ordering)
- Should follow:
  - [`0010_production_hardening_execution_sandbox.md`](../planned/0010_production_hardening_execution_sandbox.md)
- Strongly related / should be designed together:
  - [`0072_execution_security_policy_and_guardrails.md`](0072_execution_security_policy_and_guardrails.md) (shared allow/deny policy for installs + runtime)
- Related (historical context + prior thinking):
  - [`0017_dynamic_library_loading.md`](../completed/0017_dynamic_library_loading.md)

### ADR dependencies (must comply)
- **All ADRs are mandatory**: [`docs/adr/README.md`](../../adr/README.md)
- **Primary ADR dependencies**:
  - [`ADR 0001`](../../adr/0001-article-first-mixed-audience.md)
  - [`ADR 0002`](../../adr/0002-ab-testing-ladder.md)
  - [`ADR 0005`](../../adr/0005-perfect-observability.md)
  - [`ADR 0007`](../../adr/0007-permissive-licenses-and-minimal-dependencies.md)

### Points of vigilance (during execution)
- Treat package installation as a high-risk capability:
  - isolate installs from the main backend process
  - enforce timeouts, disk quotas, and allow/deny lists (policy-driven)
  - record every install event for observability/audit
- Reproducibility: record installed packages + versions per notebook/release.
- Operational safety: avoid breaking the global environment for all notebooks/users.
 - Prefer a human-owned policy file (YAML) so operators can tune risk posture without code changes:
   - deny dangerous packages and install sources
   - restrict risky primitives/commands during execution (shared with `0072`)

## References (source of truth)
- `backend/app/services/execution_service.py` (execution environment model)
- `backend/app/services/notebook_service.py::execute_cell` (execution orchestration)
- [`docs/adr/0007-permissive-licenses-and-minimal-dependencies.md`](../../adr/0007-permissive-licenses-and-minimal-dependencies.md)

## Proposal (initial; invites deeper thought)

### Context / constraints
- Users need domain libraries, but unrestricted installs create supply-chain and RCE risks.
- The project currently executes code in-process; true secure installs likely require stronger sandboxing (see backlog `0010`).

### Design options considered (with long-term consequences)
#### Option A: No user installs (rebuild images only)
- **Pros**: simplest security posture.
- **Cons / side effects**: blocks many real workflows; slow iteration.
- **Long-term consequences**: product feels “closed” compared to notebooks.

#### Option B: Allow `pip install` inside the same runtime environment (unsafe)
- **Pros**: easiest to implement; familiar to users.
- **Cons / side effects**: supply-chain risk; affects all notebooks; hard to audit/rollback; breaks reproducibility.
- **Long-term consequences**: trust and security problems.

#### Option C: Allowlisted installs into an isolated per-notebook environment (recommended)
- **Pros**: strong safety story; reproducible per-notebook env; avoids global breakage.
- **Cons / side effects**: more engineering; needs sandboxing and resource management.
- **Long-term consequences**: scalable foundation for plugins/extensions.

### Recommended approach (current best choice)
Option C, likely gated on sandbox hardening (backlog `0010`) so installs and execution run in an isolated environment with explicit allowlists.

### Testing plan (A/B/C)
> Follow the project’s testing ADR: [`docs/adr/0002-ab-testing-ladder.md`](../../adr/0002-ab-testing-ladder.md).

- **A (mock / conceptual)**:
  - define allowlist model + isolation strategy + threat model (what attacks we prevent)
- **B (real code + real examples)**:
  - implement a minimal install API with an allowlist and demonstrate installing a safe package into an isolated env
- **C (real-world / production-like)**:
  - run installs in the real deployment topology (Docker) with resource limits, logging, and a denial case (blocked package)

## Acceptance Criteria (must be fully satisfied)
- Users can request installing an allowlisted package and then import it in subsequent executions.
- Disallowed packages are blocked with a clear error message and an audit log entry.
- Install operations are isolated from the main backend runtime and are resource-limited.
- Installed package set (names + versions) is recorded per notebook and included in exports/releases.

## Implementation Notes (fill during execution)
TBD

## Full Report (fill only when moving to completed/)
TBD

