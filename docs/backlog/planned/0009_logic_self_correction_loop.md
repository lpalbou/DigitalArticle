# Backlog Item

## Title
Implement logic self-correction loop (post-success validation against intent + persona best practices)

## Backlog ID
0009

## Priority
- **P2**: high leverage for quality (“executable but wrong”), but must be built on strong observability and a stable test baseline.

## Date / Time
2026-01-31T07:45:00 (local)

## Short Summary
After code executes successfully, add a bounded loop that checks whether the analysis actually satisfies the user’s prompt and persona constraints/best practices. If not, instruct the LLM to modify the code (with reasons), rerun, and repeat until compliant or exhausted.

## Key Goals
- Catch “executable but wrong” analyses automatically.
- Enforce persona constraints/best practices explicitly.
- Preserve transparency: store evidence, decisions, and iteration traces.

## Scope

### To do
- Define a “logic compliance check” contract:
  - inputs (prompt, code, execution results, persona guidance, file context)
  - outputs (pass/fail + reasons + proposed fixes)
- Add bounded loop distinct from execution retry loop:
  - execution retry: fix runtime errors
  - logic correction: fix semantic mismatch after success
- Store artifacts (metadata + trace) for observability.

### NOT to do
- Do not create an unbounded loop (must be bounded and safe).
- Do not silently change results without showing what changed and why.

## Dependencies

### Backlog dependencies (ordering)
- Should follow:
  - [`0003_fix_test_suite_regressions.md`](../completed/0003_fix_test_suite_regressions.md)
  - [`0007_perfect_observability_llm_agentic_tracing.md`](0007_perfect_observability_llm_agentic_tracing.md) (must be debuggable/auditable)

### ADR dependencies (must comply)
- **All ADRs are mandatory**: [`docs/adr/README.md`](../../adr/README.md)
- **Primary ADR dependencies**:
  - [`ADR 0001`](../../adr/0001-article-first-mixed-audience.md)
  - [`ADR 0002`](../../adr/0002-ab-testing-ladder.md)
  - [`ADR 0003`](../../adr/0003-truncation-compaction.md)
  - [`ADR 0004`](../../adr/0004-recursive-self-correction-loop.md) (this item implements part (b))
  - [`ADR 0005`](../../adr/0005-perfect-observability.md)

### Points of vigilance (during execution)
- Must be bounded and safe: strict stop conditions and clear user-visible state.
- Must preserve trust: do not silently change results; store evidence and diffs.
- Must avoid cost explosions: include caching and minimal prompts; make token/cost visible via observability.

## References (source of truth)
- `backend/app/services/notebook_service.py`
- `backend/app/services/llm_service.py`
- `backend/app/services/persona_service.py`
- `docs/adr/0004-recursive-self-correction-loop.md`

## Proposal (initial; invites deeper thought)

### Context / constraints
- Must align with ADR 0001 (mixed-audience article-first) and ADR 0004 (proposed recursive loops).
- Must manage cost/latency trade-offs and determinism.

### Design options considered (with long-term consequences)
#### Option A: LLM-only judge + fix loop
- **Pros**: flexible across domains; captures intent well
- **Cons / side effects**: cost/latency; non-determinism; risk of over-correction
- **Long-term consequences**: high-quality but must manage stability and caching

#### Option B: Hybrid: deterministic heuristics + LLM judge (recommended)
- **Pros**: cheap checks catch obvious failures; LLM handles ambiguous cases; more stable
- **Cons / side effects**: needs careful heuristics to avoid false positives/negatives
- **Long-term consequences**: best balance of cost and correctness

#### Option C: Deterministic-only validation
- **Pros**: deterministic, cheap
- **Cons / side effects**: misses semantic mismatches; brittle
- **Long-term consequences**: limited value

### Recommended approach (current best choice)
Hybrid approach: deterministic checks for obvious mismatches + LLM judge for intent/persona compliance, with strict stopping rules and transparent artifact storage.

### Testing plan (A/B/C)
> Follow `docs/adr/0002-ab-testing-ladder.md` and ADR 0004.

- **A (mock / conceptual)**:
  - Mock examples where code is executable but violates intent/persona, and specify expected corrections.
- **B (real code + real examples)**:
  - Real notebooks + real personas; assert loop triggers on known mismatches and stops correctly.
- **C (real-world / production-like)**:
  - Run persona scenario suites with realistic datasets and confirm intent alignment and persona compliance.

## Acceptance Criteria (must be fully satisfied)
- Logic correction loop exists and is bounded.
- System differentiates runtime fixes vs logic fixes in UI/metadata.
- Artifacts are persisted for transparency (what changed, why, and evidence).

## Implementation Notes (fill during execution)
TBD

## Full Report (fill only when moving to completed/)
TBD

