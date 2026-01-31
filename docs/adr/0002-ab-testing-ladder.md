# ADR 0002: A/B/C testing ladder for backlog work

## ADR
ADR 0002

## Title
A/B/C testing ladder with increasing realism and difficulty

## Date / Time
2026-01-31T07:40:00 (local)

## Status
Accepted

## Context

Digital Article mixes product UX, LLM integration, execution, exports, and storage. Changes frequently have second-order effects (latency, correctness, safety, determinism).

We need a lightweight but consistent testing ladder to:

- validate design intent early
- reduce regressions
- ensure changes are proven in increasingly realistic conditions

## Decision

All backlog items must define and execute tests using the following ladder:

### A: Mock / conceptual validation

- May use mockups, diagrams, fake data, or minimal scaffolding.
- Goal: validate correctness of the idea and UX/architecture shape.
- Must produce a clear “pass/fail” result.

### B: Real code + real examples

- Must exercise real code paths.
- Must include concrete examples (e.g., real notebook JSON, real API calls, representative data).
- Goal: validate integration correctness.

### C: Real-world / production-like validation

- Should mimic production or real user workflows:
  - realistic datasets
  - realistic notebook sizes
  - realistic deployment topology (Docker, remote LLM, etc.)
- Goal: validate operability, performance, and end-to-end correctness.
- If C is not feasible, the backlog item must explicitly explain why.

## Options considered (with consequences)

### Option A: “Unit tests only”
- **Pros**: fast, cheap
- **Cons / side effects**: misses UX, integration, and operability failures (SSE, Docker networking, long-running flows)
- **Long-term consequences**: repeated regressions and production surprises

### Option B: A/B/C ladder (chosen)
- **Pros**: matches multi-layer system; preserves flexibility; makes trade-offs explicit
- **Cons / side effects**: requires discipline to document evidence
- **Long-term consequences**: stable process for safe iteration

## Implications

- Backlog template must include A/B/C test plan and evidence on completion.
- “Tests passed” is defined in the scope of the item:
  - For code items: unit/integration tests + A/B (and C when feasible)
  - For docs/process-only items: A/B may be sufficient if C is not applicable

## Testing strategy (A/B/C)

This ADR defines the ladder; backlog items must reference it.

## Follow-ups

- Enforce or automate checks where possible (linting, CI, structured test evidence).

