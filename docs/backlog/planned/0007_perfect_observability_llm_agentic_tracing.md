# Backlog Item

## Title
Implement perfect observability: persistent, queryable traces for all LLM + agentic calls (cell execution, tasks, flows)

## Backlog ID
0007

## Priority
- **P1**: required for responsible AI and compliance; also a force-multiplier for debugging, self-correction, and publishing provenance.

## Date / Time
2026-01-31T08:10:00 (local)

## Short Summary
Implement end-to-end observability so that every cell execution, task, and multi-step flow produces persistent, queryable traces of all LLM and agentic calls. This is required for responsible AI, debugging, and compliance/regulatory alignment.

## Key Goals
- Persist traces across restarts (no “lost history”).
- Provide a consistent hierarchy: flow → task → step (LLM/tool/execution).
- Make traces safe (redaction, access control) and auditable (no silent truncation of evidence).

## Scope

### To do
- Implement ADR 0005:
  - define trace schema (`flow_id`, `task_id`, `step_id`, parent relationships)
  - persist traces in a dedicated store (or an initial minimal store with a migration path)
  - add UI/UX access for technical users (trace viewer)
- Ensure all LLM/agentic calls emit structured trace events:
  - code generation + retries
  - review + streaming review
  - semantic extraction + streaming exports
  - model downloads
  - chat

### NOT to do
- Do not store secrets in traces (API keys must be redacted).
- Do not silently compact/truncate evidence; if compaction is needed for display, follow ADR 0003.

## Dependencies

### Backlog dependencies (ordering)
- Should follow: [`0003_fix_test_suite_regressions.md`](../completed/0003_fix_test_suite_regressions.md)
- Strongly coupled with:
  - [`0004_unify_llm_config_surfaces.md`](0004_unify_llm_config_surfaces.md) (auditable config application)
  - [`0005_unify_persistence_roots.md`](0005_unify_persistence_roots.md) (trace store placement/backup story)

### ADR dependencies (must comply)
- **All ADRs are mandatory**: [`docs/adr/README.md`](../../adr/README.md)
- **Primary ADR dependencies**:
  - [`ADR 0002`](../../adr/0002-ab-testing-ladder.md)
  - [`ADR 0003`](../../adr/0003-truncation-compaction.md)
  - [`ADR 0005`](../../adr/0005-perfect-observability.md) (this item implements it)

### Points of vigilance (during execution)
- Never persist secrets; redact API keys and sensitive headers by default.
- Do not silently truncate trace evidence; if display compaction is needed, log INFO + add `#COMPACTION_NOTICE`.
- Ensure stable identifiers (`flow_id`, `task_id`, `step_id`) and parent-child linking are enforced.

## References (source of truth)
- [`ADR 0005`](../../adr/0005-perfect-observability.md)
- `backend/app/services/llm_service.py`
- `backend/app/services/notebook_service.py`
- `backend/app/api/review.py` (streaming review traces)
- `backend/app/api/models.py` (model download traces)

## Proposal (initial; invites deeper thought)

### Context / constraints
- Must align with [`ADR 0005`](../../adr/0005-perfect-observability.md).
- Must consider retention and access control early (compliance).

### Design options considered (with long-term consequences)
#### Option A: Persist traces in notebook JSON
- **Pros**: minimal infra; self-contained
- **Cons / side effects**: bloat; hard cross-notebook querying; privacy controls hard
- **Long-term consequences**: limited compliance story at scale

#### Option B: Append-only JSONL trace store under workspace root (good first step)
- **Pros**: simple; queryable; works without DB; supports retention tooling
- **Cons / side effects**: needs indexing strategy; can grow large
- **Long-term consequences**: stable foundation; can migrate to DB later

#### Option C: Database + OpenTelemetry exporter (best long term)
- **Pros**: powerful query; operational controls; integrates with standard tooling
- **Cons / side effects**: operational complexity; schema migrations; infra dependencies
- **Long-term consequences**: strongest compliance + observability story

### Recommended approach (current best choice)
Start with Option B (append-only store + strict schema) and keep the schema compatible with later OpenTelemetry/DB migration (Option C).

### Testing plan (A/B/C)
> Follow [`docs/adr/0002-ab-testing-ladder.md`](../../adr/0002-ab-testing-ladder.md).

- **A (mock / conceptual)**:
  - define event schema; map required events for each flow
- **B (real code + real examples)**:
  - execute cells with retries; run review; run semantic export; validate trace store contains complete, linked records
- **C (real-world / production-like)**:
  - run in Docker topologies; validate retention policies, access controls, and trace export for audit

## Acceptance Criteria (must be fully satisfied)
- Every cell execution and task produces a trace with stable IDs and parent/child relationships.
- Traces persist across backend restarts.
- No secrets are stored in traces; redaction is tested.
- Compaction/truncation in traces is either absent or explicitly marked/logged per ADR 0003.

## Implementation Notes (fill during execution)

### Phase 1 Implementation (2026-02-01)

**Files created:**
- `backend/app/models/trace.py` - TraceEvent schema with hierarchy (flow/task/step), StepType enum, redaction and truncation utilities
- `backend/app/services/trace_store.py` - Singleton JSONL append-only trace store with query support
- `backend/app/api/traces.py` - REST API for querying traces (`/api/traces/query`, `/api/traces/flow/{flow_id}`, etc.)
- `tests/observability/test_trace_store.py` - 19 tests covering persistence, redaction, queries

**Files modified:**
- `backend/app/services/llm_service.py` - Added `_persist_llm_trace()` method, instrumented `agenerate_code_from_prompt()`
- `backend/app/services/notebook_service.py` - Added flow-level traces around `execute_cell()`
- `backend/app/main.py` - Registered traces router

**Schema:**
- `flow_id`: Root operation (e.g., cell execution)
- `task_id`: Sub-operation (e.g., code generation, retry)
- `step_id`: Atomic action (e.g., single LLM call)
- `parent_step_id`: Hierarchy linking

**Storage:**
- Location: `{workspace_root}/traces/traces.jsonl`
- Format: Append-only JSONL
- Rotation: Automatic at 50MB with dated archives
- Retention: 30 days default (cleanup endpoint available)

**Redaction:**
- API keys (`sk-*`, `key-*`)
- Bearer tokens
- Passwords and secrets in config strings

**Truncation (per ADR 0003):**
- Prompts: 10,000 chars max
- Responses: 20,000 chars max
- Code: 10,000 chars max
- All truncations include `#TRUNCATION_NOTICE`

**Tests:** 231 tests pass (including 19 new observability tests)

### Phase 2: UI Decision (2026-02-01)

**Decision:** Keep the existing per-cell Execution Details modal as the primary trace UI.

The per-cell view (ExecutionDetailsModal) is:
- More contextual (tied to the cell you're inspecting)
- Already has excellent UX (tabs, cost estimation, export, etc.)
- Easier to access (click on a cell)

The global TraceViewerModal was built but removed from the header because:
- It duplicated the per-cell view's functionality
- Less contextual (harder to find the trace you care about)
- Added UI clutter

**What remains:**
- `TraceStore` backend persistence (JSONL) for audit/compliance
- REST API `/api/traces/*` for programmatic access
- Per-cell view uses `cell.llm_traces` (saved with notebook JSON)
- TraceStore provides secondary audit trail independent of notebook lifecycle

**Files kept but not exposed in header:**
- `frontend/src/components/TraceViewerModal.tsx` - Available for future admin/debug use
- `frontend/src/services/api.ts::traceAPI` - API client for trace queries

## Full Report (fill only when moving to completed/)
TBD (move to completed/ after Docker validation)

