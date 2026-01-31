# ADR 0004: Recursive self-correction loops for cell execution

## ADR
ADR 0004

## Title
Two-stage recursive self-correction: (a) execution correctness and (b) logic/persona correctness

## Date / Time
2026-01-31T07:40:00 (local)

## Status
Proposed

## Context

Digital Article already supports “execution self-correction” via an auto-retry loop: if code fails, it is sent back for improvement and retried.

However, execution success does **not** guarantee that:

- the code actually does what the user requested
- the code follows domain best practices
- the methodology and results are logically coherent
- persona constraints are respected (basic and expert guidance)

To fulfill the mission in ADR 0001 (mixed audience + article-first), we need a second loop: **logic self-correction** after successful execution.

## Decision

When a cell is executed, the system should support two recursive loops:

### (a) Self-correction of execution (runtime correctness)

- If code fails to run:
  - capture error + context
  - ask LLM for corrected code
  - rerun (up to a bounded max retry count)

### (b) Self-correction of logic (semantic correctness)

Only after code runs successfully:

- Evaluate whether the produced code/results satisfy:
  - the user’s prompt intent
  - basic + expert persona constraints and best practices
  - methodological correctness (assumptions, statistical validity, etc.)
- If “no”, prompt the LLM with:
  - what to change in code and why
  - the evidence of mismatch (results/variables/outputs)
- Rerun and repeat (bounded) until:
  - intent and persona compliance is reached, or
  - the loop is exhausted and the system surfaces the mismatch transparently

## Options considered (with consequences)

### Option A: Execution-only auto-retry (status quo)
- **Pros**: simpler, cheaper, faster
- **Cons / side effects**: produces plausible-but-wrong analyses; trust failures; requires user vigilance
- **Long-term consequences**: system looks “magical” but unreliable for scientific work

### Option B: Add logic self-correction using LLM-as-judge and heuristic checks (candidate)
- **Pros**: catches incorrect intent alignment; improves rigor; better for non-technical users
- **Cons / side effects**: added latency and cost; risk of over-correction; requires careful prompt design and stopping rules
- **Long-term consequences**: higher-quality outputs, but must manage determinism and safety

### Option C: Purely deterministic validation (no LLM judge)
- **Pros**: deterministic, cheap
- **Cons / side effects**: limited ability to validate intent; brittle across domains
- **Long-term consequences**: misses the majority of semantic failures

## Implications

- Requires bounded loops and clear user-visible state:
  - “execution retry” vs “logic correction”
- Requires storing artifacts for transparency:
  - why the logic check failed
  - how the code was modified
  - which persona constraints were applied
- Must avoid silent truncation/compaction in the evidence presented (ADR 0003).

## Testing strategy (A/B/C)

Follow ADR 0002:

- **A**: mock flow + synthetic examples demonstrating both loops and stop conditions
- **B**: real code execution using representative notebooks and personas; asserts that “wrong but executable” is corrected or surfaced
- **C**: real-world dataset workflows and persona-specific scenarios with end-to-end validation

## Follow-ups

- Backlog item: implement logic self-correction loop and evidence storage.

