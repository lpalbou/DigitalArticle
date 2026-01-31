# Backlog Item

## Title
Execution security policy + guardrails (deny dangerous imports/commands; config-driven allow/deny lists)

## Backlog ID
0072

## Priority
- **P0 (proposed)**: current in-process `exec()` means a malicious or careless user can likely compromise the host/server; we need explicit guardrails and a roadmap to real isolation.

## Date / Time
2026-01-31T13:10:00 (local)

## Short Summary
Digital Article executes user/LLM-generated Python code in-process. That is a serious security risk: users can likely run OS/network commands, read/write arbitrary files, or exfiltrate secrets. Add a security backlog to investigate the execution pipeline end-to-end and implement **config-driven** guardrails (YAML allow/deny lists) for imports, builtins, filesystem paths, and network egress. This is not a substitute for true sandboxing (see backlog `0010`), but it is an urgent first line of defense and a foundation for policy enforcement (also needed for user-installed libraries).

## Key Goals
- Prevent obvious host compromise vectors (filesystem escape, subprocess, network exfiltration) as early as possible.
- Make security policy **human-owned and configurable** (YAML allow/deny lists).
- Document a clear threat model and avoid false security claims.

## Scope

### To do
- Investigate the current execution pipeline and security posture:
  - where `exec()` occurs, what globals/builtins are available, and what filesystem/network access exists
  - identify common jailbreak patterns (imports, dunder access, `__import__`, `builtins`, etc.)
- Define a security policy schema (YAML) and load/validate it at runtime:
  - **imports**: allowlist/denylist of modules/packages
  - **builtins**: allow/deny sensitive builtins (`open`, `exec`, `eval`, `compile`, etc.)
  - **filesystem**: allowed roots (workspace) vs forbidden paths (system files, secrets)
  - **network**: allow/deny outbound connections (default deny or restricted allowlist)
  - **commands**: deny dangerous patterns even if reachable indirectly (e.g., `os.system`, `subprocess.*`)
  - **install policy**: package allow/deny lists and index/source restrictions (shared with backlog `0071`)
- Implement enforcement points:
  - pre-execution static analysis (AST-based) to reject/flag dangerous patterns
  - runtime enforcement where possible (custom `__import__`, restricted builtins, chroot/container later)
  - explicit audit logs + trace events for policy decisions (allow/deny)
- Add tests:
  - denylisted import is blocked with clear error
  - denied filesystem access is blocked
  - denied network access is blocked

### NOT to do
- Do not claim “secure sandbox” if we are still executing in-process; document limitations explicitly.
- Do not hardcode allow/deny lists in code; policy must be config-driven.

## Dependencies

### Backlog dependencies (ordering)
- Related and should inform the final design:
  - [`0010_production_hardening_execution_sandbox.md`](../planned/0010_production_hardening_execution_sandbox.md)
  - [`0071_secure_user_library_installation.md`](0071_secure_user_library_installation.md)

### ADR dependencies (must comply)
- **All ADRs are mandatory**: [`docs/adr/README.md`](../../adr/README.md)
- **Primary ADR dependencies**:
  - [`ADR 0002`](../../adr/0002-ab-testing-ladder.md)
  - [`ADR 0005`](../../adr/0005-perfect-observability.md) (policy decisions must be observable/auditable)
  - [`ADR 0007`](../../adr/0007-permissive-licenses-and-minimal-dependencies.md) (policy tooling deps must be permissive)

### Points of vigilance (during execution)
- Python “sandboxing” in-process is fragile; we must be honest about guarantees.
- Guardrails should fail closed for high-risk actions, but avoid breaking common scientific workflows.
- Policy changes must be traceable and reviewable (who changed the YAML, when).

## References (source of truth)
- `backend/app/services/execution_service.py` (execution boundary; `exec()` usage)
- `backend/app/services/notebook_service.py::execute_cell` (execution orchestration)
- [`docs/backlog/planned/0010_production_hardening_execution_sandbox.md`](../planned/0010_production_hardening_execution_sandbox.md)

## Proposal (initial; invites deeper thought)

### Context / constraints
- We want to be “pretty relaxed” for normal analysis, but we must deny high-risk libraries and primitives.
- A config-driven policy allows operators to tailor risk posture for local vs production deployments.

### Design options considered (with long-term consequences)
#### Option A: Only container sandboxing (no interim guardrails)
- **Pros**: strongest long-term posture.
- **Cons / side effects**: slow to land; leaves current system exposed.
- **Long-term consequences**: risk remains until sandbox is shipped.

#### Option B: Config-driven guardrails now + sandbox later (recommended)
- **Pros**: immediate risk reduction; policy foundation reusable inside sandbox.
- **Cons / side effects**: not bulletproof; must be careful not to overpromise.
- **Long-term consequences**: scalable policy system; smoother migration to isolation.

### Recommended approach (current best choice)
Option B: introduce an operator-owned YAML policy and enforce it via static + runtime guardrails, while planning true isolation (`0010`).

### Testing plan (A/B/C)
> Follow the project’s testing ADR: [`docs/adr/0002-ab-testing-ladder.md`](../../adr/0002-ab-testing-ladder.md).

- **A (mock / conceptual)**:
  - define threat model + YAML policy schema + default allow/deny lists
- **B (real code + real examples)**:
  - implement policy load/validation and block representative dangerous code samples
- **C (real-world / production-like)**:
  - run in Docker and validate no host filesystem/network escape under policy

## Acceptance Criteria (must be fully satisfied)
- A YAML security policy exists (schema documented) and is loaded by the backend.
- Denylisted imports/commands are blocked with a clear error + audit trace.
- Policy is configurable without code changes (file-based).
- Tests cover key denial cases and do not break standard analysis flows.

## Implementation Notes (fill during execution)
TBD

## Full Report (fill only when moving to completed/)
TBD

