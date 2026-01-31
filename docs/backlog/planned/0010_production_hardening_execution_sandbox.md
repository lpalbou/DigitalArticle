# Backlog Item

## Title
Production hardening phase 1: sandbox Python execution (process/container isolation)

## Backlog ID
0010

## Priority
- **P2**: high-impact for production safety, but should follow a green test baseline and solid observability/persistence foundations.

## Date / Time
2026-01-31T07:45:00 (local)

## Short Summary
The backend currently executes generated/user code in-process (via `exec()`), which is not production-safe. Introduce sandboxing (process or container isolation) to improve security, reliability, and multi-user readiness.

## Key Goals
- Prevent untrusted code from compromising the backend process and host.
- Enable resource limits (CPU/memory/time) and file access policies.
- Preserve the current rich output capture UX as much as possible.

## Scope

### To do
- Choose sandbox strategy (subprocess, container, jailed runtime).
- Define execution API boundary (inputs/outputs, artifacts, state).
- Integrate with existing execution pipeline and persistence story.

### NOT to do
- Do not “ship” a partial sandbox that provides a false sense of security.
- Do not break core notebook UX without a migration plan.

## Dependencies

### Backlog dependencies (ordering)
- Should follow: [`0003_fix_test_suite_regressions.md`](0003_fix_test_suite_regressions.md)
- Strongly related to:
  - [`0005_unify_persistence_roots.md`](0005_unify_persistence_roots.md) (state and artifact storage)
  - [`0007_perfect_observability_llm_agentic_tracing.md`](0007_perfect_observability_llm_agentic_tracing.md) (auditability of execution)

### ADR dependencies (must comply)
- **All ADRs are mandatory**: [`docs/adr/README.md`](../../adr/README.md)
- **Primary ADR dependencies**:
  - [`ADR 0001`](../../adr/0001-article-first-mixed-audience.md) (preserve intent↔how↔what↔communication UX)
  - [`ADR 0002`](../../adr/0002-ab-testing-ladder.md)
  - [`ADR 0003`](../../adr/0003-truncation-compaction.md)
  - [`ADR 0005`](../../adr/0005-perfect-observability.md) (execution must be observable/auditable)

### Points of vigilance (during execution)
- Avoid false security claims: document threat model and boundaries explicitly.
- Ensure performance/latency regressions are measured (especially for rich output capture).
- Preserve observability and reproducibility; sandboxing must not break trace/provenance.

## References (source of truth)
- `backend/app/services/execution_service.py`
- `docs/dive_ins/execution_service.md`
- `docs/architecture.md` (execution + persistence map)

## Proposal (initial; invites deeper thought)

### Context / constraints
- Execution is a core trust boundary.
- Current architecture relies on per-notebook globals and state persistence; sandboxing changes this fundamentally.

### Design options considered (with long-term consequences)
#### Option A: Subprocess-based execution (one worker process per notebook)
- **Pros**: simpler than containers; works locally; can enforce timeouts; improves crash isolation
- **Cons / side effects**: still shares host filesystem unless restricted; harder to lock down; state persistence is more complex
- **Long-term consequences**: good intermediate step; may not satisfy strict security requirements

#### Option B: Container-based execution (per notebook or shared pool)
- **Pros**: strongest isolation; clear resource policies; aligns with production needs
- **Cons / side effects**: operational complexity; scheduling/cleanup; performance overhead
- **Long-term consequences**: best for production/multi-user; requires orchestration design

#### Option C: Keep in-process and “sanitize” (not acceptable)
- **Pros**: minimal change
- **Cons / side effects**: insecure; unreliable; does not meet production expectations
- **Long-term consequences**: blocks serious adoption

### Recommended approach (current best choice)
Start with a subprocess execution boundary for near-term stability, but design the interface to be container-ready so we can migrate to container isolation without rewriting the system.

### Testing plan (A/B/C)
> Follow `docs/adr/0002-ab-testing-ladder.md`.

- **A (mock / conceptual)**:
  - Threat model and architecture diagrams; define the execution boundary.
- **B (real code + real examples)**:
  - Execute representative notebooks; validate output capture and state handling.
  - Verify timeouts and resource caps.
- **C (real-world / production-like)**:
  - Validate under Docker with realistic loads and adversarial code samples.

## Acceptance Criteria (must be fully satisfied)
- Execution is isolated from the backend process (crashes and memory leaks do not take down the API).
- Resource limits are enforceable and tested.
- A clear threat model and constraints are documented.

## Implementation Notes (fill during execution)
TBD

## Full Report (fill only when moving to completed/)
TBD

