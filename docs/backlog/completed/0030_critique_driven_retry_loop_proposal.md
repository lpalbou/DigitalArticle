# Backlog Item (Historical; migrated from legacy planning)

## Title
Critique-Driven Retry Loop: The Missing "Last Mile"

## Backlog ID
0030

## Priority
- **P2 (historical)**: migrated record from the legacy `docs/planning/` folder to keep governance artifacts in one system.

## Date / Time
Unknown (historical; migrated 2026-01-31)

## Short Summary
This file preserves a historical planning/proposal document that previously lived under `docs/backlog/completed/0030_critique_driven_retry_loop_proposal.md`. It has been migrated to `docs/backlog/completed/` so older design artifacts live under the backlog governance system.

## Key Goals
- Preserve historical context without losing information.
- Reduce confusion by removing `docs/planning/` from the active doc graph.
- Keep references navigable.

## Scope

### To do
- Preserve the original planning content under **Full Report** (verbatim aside from link-path adjustments due to relocation).
- Update references elsewhere in the docs to point to this new location.

### NOT to do
- Do not claim the underlying plan is current or implemented.

## Dependencies

### Backlog dependencies (ordering)
- **None**

### ADR dependencies (must comply)
- **All ADRs are mandatory**: [`docs/adr/README.md`](../../adr/README.md)

### Points of vigilance (during execution)
- Keep the historical record intact.
- Ensure any updated links remain valid (run `python tools/validate_markdown_links.py`).

## References (source of truth)
- Legacy source: `docs/backlog/completed/0030_critique_driven_retry_loop_proposal.md` (removed after migration)
- Canonical docs: [`docs/overview.md`](../../overview.md), [`docs/architecture.md`](../../architecture.md)

## Full Report (legacy planning content)

# Critique-Driven Retry Loop: The Missing "Last Mile"

> **Status**: Planning / proposal.  
> This document is not a description of current behavior; it proposes a future “critique-driven” retry loop.  
> For current execution + retry behavior, see `docs/dive_ins/notebook_service.md` and `docs/error-handling.md`.

## Executive Summary

The current `improve-reasoningv2` branch implements a robust **Linear Reasoning Pipeline**:
`Plan` → `Generate` → `Execute` → `Critique`

However, it lacks a **Self-Correction Loop** for logical errors. While the system identifies invalid results (e.g., "R-squared is negative"), it does not automatically attempt to fix them. It merely logs them and saves them to metadata.

This document outlines the design for closing this loop, turning the `Critic` into an active agent that enforces quality.

## Current State vs. Desired State

### Current State (Linear)
1.  **Execute Code**: `result = execute(code)`
2.  **Check Status**: If `result.status == ERROR` (Syntax Error), retry automatically.
3.  **Critique**: If `result.status == SUCCESS`, run `AnalysisCritic`.
4.  **Outcome**: If `AnalysisCritic` finds critical issues, they are logged and stored, but the cell status remains `SUCCESS`. The user must manually read the warning and ask for a fix.

### Desired State (Cyclic)
1.  **Execute Code**: `result = execute(code)`
2.  **Critique**: If `result.status == SUCCESS`, run `AnalysisCritic`.
3.  **Assessment**:
    *   If `critique.has_critical_issues()` is **True**:
        *   Treat this as a "Logical Execution Error".
        *   **Action**: Trigger the existing auto-retry mechanism.
        *   **Feedback**: Pass the specific critique findings to the LLM as the "error message".

## Implementation Plan

### 1. Modification in `notebook_service.py`

The change is primarily located in the `execute_cell` method, specifically in the post-execution block.

**Current Code (Pseudo-code):**
```python
# ... execution ...
if result.status == SUCCESS:
    critique = critic.critique_analysis(...)
    cell.metadata['critique'] = critique
    if critique.has_critical_issues():
        logger.warning("Critical issues found")
    # END - Cell is marked SUCCESS
```

**Proposed Integration (Pseudo-code):**
```python
# ... execution ...
if result.status == SUCCESS:
    critique = critic.critique_analysis(...)
    
    if critique.has_critical_issues():
        # 1. Construct a "Scientific Error" message
        findings_text = "\n".join([f"- {f.title}: {f.explanation}" for f in critique.critical_findings])
        error_msg = f"SCIENTIFIC VALIDITY CHECK FAILED:\n{findings_text}\n\nPlease fix the code to resolve these methodological issues."
        
        # 2. Mutate the result to simulate a failure
        result.status = ExecutionStatus.ERROR
        result.error_message = error_msg
        result.error_type = "ScientificValidityError"
        
        # 3. Set retry flags to trigger the existing while-loop
        should_auto_retry = (cell.retry_count < max_retries)
        
        # 4. Log
        logger.info(f"🔄 Triggering auto-retry due to critique: {error_msg}")
```

### 2. Integration with `LLMService.suggest_improvements`

The existing `suggest_improvements` method expects standard Python tracebacks. We need to ensure it handles "ScientificValidityError" gracefully.

**Enhancement in `_enhance_error_context`:**
Currently, `ErrorAnalyzer` parses Python tracebacks. It should be updated to recognize `ScientificValidityError` and pass the `error_message` (which contains the critique) directly to the prompt without trying to parse a stack trace that doesn't exist.

### 3. Safeguards

Critiques can sometimes be subjective or false positives. To prevent infinite loops or degradation:

1.  **Max Critique Retries**: Limit logical retries to 1 or 2 (fewer than syntax retries).
2.  **User Override**: If the user explicitly runs the cell again without changing the prompt, bypass the critique blocker.
3.  **Confidence Threshold**: Only trigger retry if `critique.confidence_in_findings` is High.

## Why This Matters

Without this loop, the `AnalysisCritic` is a passive observer. With this loop, the system becomes **agentic**:

*   **Example**:
    *   **User**: "Calculate correlation."
    *   **LLM**: Calculates correlation on categorical data (returns error or nonsense).
    *   **Critic**: "Cannot calculate Pearson correlation on string columns."
    *   **Retry**: LLM sees critique -> Changes method to Cramer's V or Chi-Square -> Re-runs.
    *   **Result**: Valid analysis without user intervention.

