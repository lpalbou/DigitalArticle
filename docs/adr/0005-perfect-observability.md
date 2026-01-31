# ADR 0005: Perfect observability for all LLM + agentic calls (ethics + compliance)

## ADR
ADR 0005

## Title
Perfect observability for each cell execution, task, and flow (LLM + agentic traces)

## Date / Time
2026-01-31T08:05:00 (local)

## Status
Accepted

## Context

Digital Article performs LLM-driven and agentic work (prompt→code, retries, review, semantic extraction, model downloads, chat). For responsible AI, debugging, and regulated environments, we must be able to answer:

- **What happened?** (which steps ran, in what order)
- **Why did it happen?** (which prompt/context/instructions caused it)
- **With what model/settings?** (provider, model, base URL, temperature, tokens, versions)
- **What did it produce?** (outputs, decisions, intermediate artifacts)
- **Who/what triggered it?** (user action, background task, retry loop, derived workflow)

This is required for:

1. **Responsible work and ethics**: transparency for technical review and debugging.
2. **Compliance / regulatory alignment** (e.g., EU AI Act style expectations): traceability and auditability.

## Decision

Digital Article should implement **end-to-end, persistent, queryable observability** for:

- each **cell execution**
- each **task** (export, review, semantic extraction, model download, chat)
- each **flow** (multi-step end-to-end user operations)

This includes LLM and agentic calls, with consistent identifiers and relationships:

- `flow_id` (root)
- `task_id` (major operation within a flow)
- `step_id` (LLM call / tool call / execution step)
- `parent_step_id` (hierarchy)

Traces must be:

- **persistent** (not just in-memory)
- **linked** to the notebook/cell/task that produced them
- **complete enough** to explain behavior (without silent truncation)
- **safe** (secrets redacted; data governance)

## Options considered (with consequences)

### Option A: In-memory traces only (status quo style)
- **Pros**: minimal overhead
- **Cons / side effects**: not auditable; lost on restart; not compliance-ready
- **Long-term consequences**: recurring “can’t reproduce/understand” incidents

### Option B: Persist traces inside notebook JSON only
- **Pros**: easy to ship; self-contained per notebook; works offline
- **Cons / side effects**: notebook files can bloat; hard to query across notebooks; privacy/retention are messy
- **Long-term consequences**: scaling pain; limited audit/query capabilities

### Option C: Dedicated trace store (recommended)
- **Pros**: queryable; scalable; supports retention/access controls; can integrate with OpenTelemetry later
- **Cons / side effects**: requires schema and migration; adds operational surface area
- **Long-term consequences**: durable foundation for compliance and continuous improvement

## Implications

- **Security/privacy**:
  - API keys must never be stored in plaintext traces.
  - PII handling rules must be explicit (redaction and access control).
- **Correctness**:
  - No silent truncation of “evidence” for audits; if compaction is required for display, it must follow [`ADR 0003`](0003-truncation-compaction.md).
- **UX**:
  - Technical users need a reliable trace viewer that can show parent/child steps and payload diffs.

## Testing strategy (A/B/C)

Follow [`ADR 0002`](0002-ab-testing-ladder.md).

- **A**: design a trace schema + diagrams for key flows (execute, retry, review, export).
- **B**: instrument real code paths (at least execute cell + retry + one streaming task) and assert traces are persisted and navigable.
- **C**: run realistic notebooks + Docker deployments and validate trace retention, access controls, and exportability for audit.

## Follow-ups

- Backlog item: implement the observability system and trace store (schema, persistence, UI viewer):
  - [`docs/backlog/planned/0007_perfect_observability_llm_agentic_tracing.md`](../backlog/planned/0007_perfect_observability_llm_agentic_tracing.md)

