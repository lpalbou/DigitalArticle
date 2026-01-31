# ADR 0003: Truncation and compaction policy

## ADR
ADR 0003

## Title
No truncation for data ingest/querying; explicit truncation/compaction only for rendering or explicit user constraints

## Date / Time
2026-01-31T07:40:00 (local)

## Status
Accepted

## Context

Truncation is a common source of silent correctness bugs:

- “Data ingest” failures: partial reads, missing rows/columns, silent corruption.
- “Data querying” failures: returning partial datasets or incomplete results.

In Digital Article, correctness and trust are critical. If truncation is applied silently, the user cannot distinguish:

- “the system decided to hide information” vs
- “the data does not contain information”

We also have LLM-context constraints where **compaction** (lossless or controlled-lossy) may be acceptable when explicitly scoped (e.g., user chooses smaller context).

## Decision

### 1) Hard rule: no truncation for data ingest and data querying

- Truncation must **never** be used for:
  - file ingest (loading datasets, parsing, imports)
  - data querying (computations, aggregations, selection)

### 2) Truncation is only acceptable for rendering/layout

Examples:

- UI display of large outputs (tables/plots/logs)
- displaying preview windows

### 3) If truncation becomes necessary (or user-requested)

Apply these rules:

1. Prefer **compaction** over truncation when possible (e.g., summarization, schema extraction, statistics).
2. Always log at **INFO** when truncation or compaction occurs.
3. Mark the code with a searchable comment:
   - `#TRUNCATION_NOTICE: <reason>`
   - `#COMPACTION_NOTICE: <reason>`

This enables repo-wide auditing with grep.

## Options considered (with consequences)

### Option A: Allow truncation anywhere for “performance”
- **Pros**: quick performance wins in the short term
- **Cons / side effects**: silent correctness loss; irreproducible results; user distrust
- **Long-term consequences**: systemic reliability issues and scientific invalidation

### Option B: Strict “no truncation for ingest/query” + explicit rendering-only truncation (chosen)
- **Pros**: preserves correctness; makes trade-offs explicit; supports trust
- **Cons / side effects**: may require optimizations (streaming, pagination, compaction) rather than truncation
- **Long-term consequences**: stable correctness guarantees and auditable behavior

## Implications

- Any existing truncation in ingest/query must be removed or refactored.
- Rendering pipelines should favor:
  - pagination
  - schema + sample + statistics
  - explicit “show more” UX
- LLM-context building may use compaction with explicit log + marker.

## Testing strategy (A/B/C)

Follow ADR 0002. For truncation/compaction changes:

- **A**: mock examples of “before/after” outputs and log records
- **B**: unit/integration tests verifying no truncation in ingest/query paths
- **C**: real-world dataset ingestion and queries (large files) with correct results

## Follow-ups

- Backlog item: audit and enforce truncation/compaction rules across codebase.

