# Backlog Item (Historical; migrated from legacy planning)

## Title
Priority 1: Async LLM Calls + Smart Auto-Save

## Backlog ID
0028

## Priority
- **P2 (historical)**: migrated record from the legacy `docs/planning/` folder to keep governance artifacts in one system.

## Date / Time
2025-12-16 (historical; migrated 2026-01-31)

## Short Summary
This file preserves a historical planning/proposal document that previously lived under `docs/backlog/completed/0028_async_llm_calls_smart_autosave.md`. It has been migrated to `docs/backlog/completed/` so older design artifacts live under the backlog governance system.

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
- Legacy source: `docs/backlog/completed/0028_async_llm_calls_smart_autosave.md` (removed after migration)
- Canonical docs: [`docs/overview.md`](../../overview.md), [`docs/architecture.md`](../../architecture.md)

## Full Report (legacy planning content)

# Priority 1: Async LLM Calls + Smart Auto-Save

> **Status**: Planning / historical context.  
> The codebase has since implemented async LLM calls in multiple endpoints and services. Treat this as a design note, not the canonical description.  
> For current execution flow, see `docs/dive_ins/notebook_service.md` and `docs/dive_ins/llm_service.md`.

**Status**: Planning
**Created**: 2025-12-16
**Priority**: CRITICAL - Causes application crashes

---

## Problem Statement

### Symptoms
- Application crashes with `ERR_NETWORK_CHANGED` during cell execution
- Browser shows "Network error: Unable to connect to server"
- Auto-save requests timeout while LLM is processing
- Other API calls (LLM status polling) fail during execution

### Root Cause

**BLOCKING SYNCHRONOUS LLM CALLS IN ASYNC HANDLERS**

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Current Flow (BROKEN)                                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  [Browser]                                                              │
│     │                                                                   │
│     ├──▶ POST /cells/execute ────────▶ [FastAPI async handler]         │
│     │                                        │                         │
│     ├──▶ PUT /notebooks (auto-save)          │ BLOCKED! Waiting for    │
│     │    ↳ Times out → ERR_NETWORK           │ sync llm.generate()     │
│     │                                        │ (10-60 seconds)         │
│     ├──▶ GET /llm/status                     │                         │
│     │    ↳ Times out → ERR_NETWORK           ▼                         │
│     │                                   [Response finally arrives]     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Code path:**
1. `cells.py:179` - `async def execute_cell()` - FastAPI async endpoint
2. `cells.py:184` - `notebook_service.execute_cell()` - SYNC call!
3. `notebook_service.py:781` - `def execute_cell()` - SYNC method
4. `llm_service.py:237` - `self.llm.generate()` - **BLOCKING HTTP CALL**

**Why this breaks everything:**
- Uvicorn runs with 1 worker (default)
- Single worker can only process 1 request at a time
- When `llm.generate()` blocks for 10-60 seconds, ALL other requests wait
- Browser has ~30s timeout → connection dies → `ERR_NETWORK_CHANGED`

---

## Solution

### Part 1: Use AbstractCore's Async API

AbstractCore v2.6.0+ provides `agenerate()` - an async version of `generate()`:

```python
# Current (BLOCKING - breaks event loop)
response = self.llm.generate(prompt, system_prompt=..., **kwargs)

# Fixed (NON-BLOCKING - keeps event loop responsive)
response = await self.llm.agenerate(prompt, system_prompt=..., **kwargs)
```

**AbstractCore Async Performance** (from docs/async-guide.md):

| Provider | Native Async | Performance Improvement |
|----------|--------------|-------------------------|
| Ollama | ✅ Yes (httpx.AsyncClient) | **7.5x faster** |
| LMStudio | ✅ Yes (httpx.AsyncClient) | **6.5x faster** |
| OpenAI | ✅ Yes (AsyncOpenAI) | **6.0x faster** |
| Anthropic | ✅ Yes (AsyncAnthropic) | **7.4x faster** |
| MLX | ⚠️ Fallback (asyncio.to_thread) | Keeps event loop responsive |
| HuggingFace | ⚠️ Fallback (asyncio.to_thread) | Keeps event loop responsive |

**API Compatibility:**
```python
# Sync API
response = llm.generate(prompt, system_prompt=..., max_tokens=..., temperature=...)

# Async API (identical signature)
response = await llm.agenerate(prompt, system_prompt=..., max_tokens=..., temperature=...)
```

### Part 2: Smart Auto-Save

**Current behavior (causes conflicts):**
- Auto-save triggers on ANY `setHasUnsavedChanges(true)` change
- 2-second debounce timer
- Triggers during cell execution → conflicts with blocked event loop

**New behavior:**
- Auto-save ONLY after successful cell execution with methodology
- No auto-save during execution (avoids concurrent request conflicts)
- Keep manual save button for explicit saves

---

## Files to Modify

### Backend - Async LLM

| File | Current | Change |
|------|---------|--------|
| `backend/app/services/llm_service.py` | `llm.generate()` x5 | Add `agenerate_*` async methods |
| `backend/app/services/notebook_service.py` | `def execute_cell()` | `async def execute_cell()` |
| `backend/app/api/cells.py` | `notebook_service.execute_cell()` | `await notebook_service.execute_cell()` |
| `backend/app/services/review_service.py` | `llm.generate()` x4 | `await llm.agenerate()` |
| `backend/app/services/chat_service.py` | `llm.generate()` x1 | `await llm.agenerate()` |
| `backend/app/services/llm_semantic_extractor.py` | `llm.generate()` x1 | `await llm.agenerate()` |
| `backend/app/services/llm_profile_extractor.py` | `llm.generate()` x1 | `await llm.agenerate()` |
| `backend/app/services/analysis_planner.py` | `session.generate()` x4 | `await session.agenerate()` |
| `backend/app/api/ai_code_fix.py` | `llm.generate()` x2 | `await llm.agenerate()` |

### Frontend - Smart Auto-Save

| File | Current | Change |
|------|---------|--------|
| `frontend/src/components/NotebookContainer.tsx` | Auto-save on `hasUnsavedChanges` | Auto-save after successful execution only |

---

## Implementation Details

### 1. LLMService Async Methods

```python
# backend/app/services/llm_service.py

async def agenerate_code_from_prompt(
    self,
    prompt: str,
    context: Optional[Dict[str, Any]] = None,
    step_type: str = 'code_generation',
    attempt_number: int = 1
) -> Tuple[str, Optional[float], Optional[str], Optional[Dict[str, Any]]]:
    """
    Async version - doesn't block event loop.
    """
    if not self.llm:
        raise LLMError(f"LLM provider '{self.provider}' is not available.")

    system_prompt = self._build_system_prompt(context)
    user_prompt = self._build_user_prompt(prompt, context)

    generation_params = {
        "max_tokens": 32000,
        "max_output_tokens": 8192,
        "temperature": 0.1
    }

    # Use async agenerate()
    response = await self.llm.agenerate(
        user_prompt,
        system_prompt=system_prompt,
        trace_metadata={
            'step_type': step_type,
            'attempt_number': attempt_number,
            'notebook_id': context.get('notebook_id') if context else None,
            'cell_id': context.get('cell_id') if context else None
        },
        **generation_params
    )

    # Extract code from response (same as sync version)
    code = self._extract_code_from_response(response.content)
    return code, response.usage.get('total_time_ms'), response.trace_id, response.full_trace
```

### 2. NotebookService Async execute_cell

```python
# backend/app/services/notebook_service.py

async def execute_cell(self, request: CellExecuteRequest) -> Optional[tuple[Cell, ExecutionResult]]:
    """
    Async cell execution - doesn't block other requests.
    """
    # ... (cell lookup, context building - same as before) ...

    # Generate code (NON-BLOCKING)
    if not cell.code or request.force_regenerate:
        code, time_ms, trace_id, full_trace = await self.llm_service.agenerate_code_from_prompt(
            cell.prompt,
            context=context,
            step_type='code_generation'
        )
        cell.code = code

    # Execute code (can stay sync - runs in process, not HTTP)
    result = self.execution_service.execute_code(cell.code, str(cell.id), str(notebook.id))

    # Generate methodology (NON-BLOCKING)
    if result.status == ExecutionStatus.SUCCESS and cell.prompt:
        explanation = await self.llm_service.agenerate_scientific_explanation(
            cell.prompt,
            cell.code,
            execution_data,
            context
        )
        cell.scientific_explanation = explanation

    return cell, result
```

### 3. Smart Auto-Save

```typescript
// frontend/src/components/NotebookContainer.tsx

const executeCell = useCallback(async (cellId: string, action: 'execute' | 'regenerate' = 'execute') => {
    // ... (mark cell executing) ...

    try {
        const response = await cellAPI.execute({
            cell_id: cellId,
            force_regenerate: action === 'regenerate'
        })

        // Check for SUCCESSFUL execution WITH methodology
        const isSuccessful = response.result.status === 'success'
        const hasMethodology = response.cell.scientific_explanation?.trim()

        // Update notebook state
        // ... (existing state update logic) ...

        // AUTO-SAVE ONLY after successful execution with methodology
        if (isSuccessful && hasMethodology) {
            await saveNotebook()
            console.log('✅ Auto-saved after successful execution with methodology')
        }

    } catch (err) {
        // Error - NO auto-save
        console.log('❌ Execution failed - not saving')
        // ... (error handling) ...
    }
}, [notebook, saveNotebook])

// REMOVE or modify the useEffect that auto-saves on hasUnsavedChanges
// Keep it only for title/description changes, not during execution
```

---

## Testing

### 1. Concurrent Request Test
```bash
# Terminal 1: Start execution
curl -X POST http://localhost:8000/api/cells/execute -d '{"cell_id": "..."}' &

# Terminal 2: Verify other requests work during execution
curl http://localhost:8000/api/llm/status  # Should respond immediately
curl http://localhost:8000/health  # Should respond immediately
```

### 2. Auto-Save Test
```
1. Execute cell that will fail → verify NO auto-save triggered
2. Execute cell that succeeds but no methodology → verify NO auto-save
3. Execute cell that succeeds with methodology → verify auto-save happens
```

### 3. Error Handling Test
```
1. Kill LLM server during execution → verify graceful error handling
2. Network timeout → verify error message shown to user
```

---

## Expected Outcome

After implementation:
- ✅ No more `ERR_NETWORK_CHANGED` crashes
- ✅ Other API calls respond during LLM execution
- ✅ Auto-save only happens after successful execution
- ✅ 6-7x performance improvement for concurrent LLM calls
- ✅ Event loop stays responsive at all times

---

## References

- AbstractCore async docs: `/workspaces/workspaces/abstractcore/docs/async-guide.md`
- AbstractCore base provider: `/workspaces/workspaces/abstractcore/abstractcore/providers/base.py:1467`
- FastAPI async best practices: https://fastapi.tiangolo.com/async/

