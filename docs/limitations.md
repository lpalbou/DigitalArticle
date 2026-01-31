# Limitations and production readiness

> **Status (2026-01-31):** Digital Article is a **research prototype / beta**. This page lists the current limitations and what “production-ready” would require.

## Summary

Digital Article is designed to bridge the gap between **doing the analysis** and **writing/publishing the article** (see [`docs/adr/0001-article-first-mixed-audience.md`](adr/0001-article-first-mixed-audience.md)).  
However, today it is best suited for **single-user** (or small, trusted-team) usage.

## Known limitations (current)

- ⚠️ **Single-user deployment only** (no multi-user authentication/authorization)
- ⚠️ **Code execution runs in the same process as the server** (not production-safe)
- ⚠️ **JSON file storage** (not scalable to many notebooks/users without a DB layer)
- ⚠️ **No real-time collaboration**
- ⚠️ **LLM latency** makes it unsuitable for real-time applications

## Production readiness (what would be required)

Digital Article can evolve toward production readiness, but it requires explicit architectural hardening:

- **Sandboxed execution** (process/container isolation + resource limits)  
  - See backlog: [`docs/backlog/planned/0010_production_hardening_execution_sandbox.md`](backlog/planned/0010_production_hardening_execution_sandbox.md)
- **Persistence scalability** (move beyond JSON-only storage when needed; clarify canonical persistence roots)  
  - See backlog: [`docs/backlog/planned/0005_unify_persistence_roots.md`](backlog/planned/0005_unify_persistence_roots.md)
- **Auth and multi-user readiness** (not implemented yet)
- **Observability / traceability** of agentic + LLM operations (for debugging + compliance)  
  - ADR: [`docs/adr/0005-perfect-observability.md`](adr/0005-perfect-observability.md) (Accepted)  
  - Backlog: [`docs/backlog/planned/0007_perfect_observability_llm_agentic_tracing.md`](backlog/planned/0007_perfect_observability_llm_agentic_tracing.md)

For deployment-oriented details, see:

- [`docs/architecture.md#deployment-considerations`](architecture.md#deployment-considerations)
- [`docs/docker-containerization.md`](docker-containerization.md)

## Where to track improvements

- **Planned backlog**: [`docs/backlog/planned/`](backlog/planned/)
- **Proposed backlog (needs review)**: [`docs/backlog/proposed/`](backlog/proposed/)

