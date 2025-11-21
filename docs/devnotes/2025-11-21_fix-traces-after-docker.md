# LLM Trace Fix - Docker/Ollama Deployment

**Date**: 2025-11-21
**Issue**: LLM execution traces not appearing in the UI after switching from LMStudio (host) to Ollama (Docker)
**Root Cause**: AbstractCore version mismatch between host and Docker container
**Status**: ✅ **FIXED**

## Problem Identification

### Symptoms
- TRACE button missing from cell headers in the UI
- No LLM trace data saved in `cell.llm_traces` field
- Traces worked with LMStudio but not with Ollama in Docker

### Investigation Process

1. **Verified trace infrastructure**: Code had tracing enabled (`enable_tracing=True`)
2. **Checked notebooks on host**: Found old notebooks with LMStudioProvider traces
3. **Checked notebooks in Docker**: Found 0 traces in active notebooks
4. **Tested Ollama provider**: Discovered `get_traces()` method was missing
5. **Version comparison**:
   - **Host**: AbstractCore 2.5.3 (local dev) ✅ Has tracing
   - **Docker**: AbstractCore 2.5.2 (from PyPI) ❌ No tracing

## Root Cause

AbstractCore 2.5.2 (used in Docker) did not have tracing support. Tracing was added in AbstractCore 2.5.3.

The host environment was using a local development version of AbstractCore 2.5.3 with tracing, while the Docker container was using the older PyPI version 2.5.2 without tracing.

## Solution

### Changes Made

1. **Updated pyproject.toml** (`backend/pyproject.toml` line 23):
   ```diff
   -    "abstractcore==2.5.2",
   +    "abstractcore>=2.5.3",  # Requires 2.5.3+ for tracing support
   ```

2. **Rebuilt Docker backend image**:
   ```bash
   docker-compose build backend --no-cache
   ```

3. **Restarted backend container**:
   ```bash
   docker-compose up -d backend
   ```

### Verification

✅ **AbstractCore version upgraded**:
```bash
$ docker exec digitalarticle-backend python3 -c "import abstractcore; print(abstractcore.__version__)"
AbstractCore version: 2.5.3
```

✅ **Tracing methods now available**:
```bash
$ docker exec -w /app/backend digitalarticle-backend python3 -c "..."
LLM type: OllamaProvider
Has get_traces: True
Has _traces: True
Has _capture_trace: True
```

## How Traces Work

### Backend Flow

1. **Initialization** (`llm_service.py` lines 56-75):
   - LLM created with `enable_tracing=True` and `max_traces=100`
   - Creates ring buffer for last 100 interactions

2. **Code Generation** (`llm_service.py` lines 206-217):
   - Calls `llm.generate()` with `trace_metadata` containing step_type, attempt_number, notebook_id, cell_id
   - Response includes `trace_id` in `response.metadata`

3. **Trace Retrieval** (`llm_service.py` lines 268-277):
   - Calls `llm.get_traces(trace_id=trace_id)` to fetch full trace
   - Returns complete trace with prompt, system_prompt, response, parameters, usage

4. **Trace Storage** (`notebook_service.py` line 894):
   - Stores trace in `cell.llm_traces` (persisted to JSON)
   - Each trace is a complete record of LLM interaction

### Frontend Flow

1. **TRACE Button** (`PromptEditor.tsx` lines 231-240):
   - Shows when `cell.llm_traces && cell.llm_traces.length > 0`
   - Displays trace count badge
   - Triggers `viewCellTraces(cell.id)` on click

2. **Execution Details Modal** (`ExecutionDetailsModal.tsx`):
   - Fetches traces from backend API: `GET /api/cells/{cellId}/traces`
   - Displays 4 tabs: LLM Traces, Console Output, Warnings, Variables
   - Shows trace details: prompt, system prompt, response, parameters, JSON

## Files Modified

- `backend/pyproject.toml`: Updated AbstractCore dependency
- Docker image: Rebuilt with AbstractCore 2.5.3

## Testing Checklist

To verify traces are working after the fix:

1. ✅ **Execute a new cell** in the notebook
2. ✅ **Check for TRACE button** next to the copy button (should show count badge)
3. ✅ **Click TRACE** to open Execution Details modal
4. ✅ **Verify traces** are shown in "LLM Traces" tab
5. ✅ **Check notebook JSON** file contains `llm_traces` array

## Future Prevention

- Pin AbstractCore to `>=2.5.3` in requirements
- Document minimum version requirements
- Add version check in CI/CD pipeline

## Notes

- Ollama container was NOT touched - the 18GB model remains intact
- Only backend container was rebuilt
- All existing notebooks retain their old traces (from LMStudio)
- New executions with Ollama will now create traces

## References

- AbstractCore 2.5.3 release: Added comprehensive tracing support for all providers
- Digital Article codebase: Uses AbstractCore for LLM abstraction
- Trace storage: Cell model field `llm_traces: List[Dict[str, Any]]`
