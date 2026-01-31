# Backlog Item (Historical; migrated from legacy devnotes)

## Title
Execution Context Persistence Issue

## Backlog ID
0019

## Priority
- **P2 (historical)**: migrated record from the legacy `docs/devnotes/` folder to keep governance artifacts in one system.

## Date / Time
Unknown (historical; migrated 2026-01-31)

## Short Summary
This file preserves a historical devnote that previously lived under `docs/backlog/completed/0019_execution_context_persistence.md`. It has been migrated to `docs/backlog/completed/` so that historical investigations and fixes live under the same backlog governance system.

## Key Goals
- Preserve historical context without losing information.
- Keep the repository’s documentation graph navigable (no legacy devnotes folder).
- Enable future follow-up backlog items to reference this historical record.

## Scope

### To do
- Preserve the original devnote content under **Full Report** (verbatim aside from link-path adjustments due to relocation).
- Update references elsewhere in the docs to point to this new location.

### NOT to do
- Do not claim this migration implies the underlying runtime change is still current; treat as historical evidence.

## Dependencies

### Backlog dependencies (ordering)
- **None**

### ADR dependencies (must comply)
- **All ADRs are mandatory**: [`docs/adr/README.md`](../../adr/README.md)

### Points of vigilance (during execution)
- Keep the historical record intact.
- Ensure any updated links remain valid (run `python tools/validate_markdown_links.py`).

## References (source of truth)
- Legacy source: `docs/backlog/completed/0019_execution_context_persistence.md` (removed after migration)
- Backlog/ADR governance: [`docs/backlog/README.md`](../README.md), [`docs/adr/README.md`](../../adr/README.md)

## Full Report (legacy devnote content)

# Execution Context Persistence Issue

> **Devnote (historical):** This file captures a past investigation. For current execution context behavior, see `backend/app/services/notebook_service.py::_build_execution_context()` and `docs/dive_ins/notebook_service.md`.

## Problem

When reloading a notebook (page refresh, backend restart, etc.), the LLM loses awareness of variables computed in previous cells, requiring users to regenerate the entire notebook.

## Root Cause

### Current Architecture

```
NotebookService (singleton)
  ├── ExecutionService (singleton, shared across ALL notebooks)
  │     └── globals_dict (in-memory Python execution context)
  └── Multiple Notebooks
        ├── Notebook A
        ├── Notebook B
        └── Notebook C
```

**The Problem:**
1. **Single Shared Context**: All notebooks share ONE `ExecutionService` with ONE `globals_dict`
2. **No Persistence**: The `globals_dict` (Python variables) is NEVER saved to disk
3. **Lost on Reload**: When backend restarts or page reloads:
   - `ExecutionService` is re-initialized
   - `globals_dict` becomes empty `{}`
   - All variables from previous executions are lost
   - LLM can't see variables that were computed before

### Evidence

**File:** `backend/app/services/notebook_service.py:62`
```python
self.execution_service = ExecutionService()  # ONE instance for all notebooks
```

**File:** `backend/app/services/execution_service.py:74`
```python
self.globals_dict = self._initialize_globals()  # Starts empty every time
```

**File:** `backend/app/services/notebook_service.py:208-210`
```python
variables = self.execution_service.get_variable_info()
if variables:
    context['available_variables'] = variables  # Will be empty after reload!
```

### What Gets Saved vs Lost

**Saved to Disk (notebooks/*.json):**
- ✅ Cell prompts
- ✅ Generated code
- ✅ Execution results (stdout, stderr, plots, tables)
- ✅ Cell execution count
- ✅ Cell state (pending, success, error)

**NOT Saved (Lost on Reload):**
- ❌ Python variables (df, model, data, etc.)
- ❌ Imported modules state
- ❌ Matplotlib figure objects
- ❌ Any in-memory data structures

### User Impact

**Scenario:**
1. User creates cells 1-5, computing: `df → cleaned_df → model → predictions`
2. Variables exist in `globals_dict`: `{'df': DataFrame, 'model': LogisticRegression, ...}`
3. User refreshes page or backend restarts
4. User creates cell 6 asking: "Plot predictions against actual values"
5. **LLM generates code using `predictions`** ← Variable doesn't exist!
6. **Code execution fails**: `NameError: name 'predictions' is not defined`
7. User must regenerate entire notebook from cell 1

## Potential Solutions

### Option 1: Persist Execution State (Complex)

**Approach**: Serialize `globals_dict` to disk and restore on load

**Pros:**
- Variables available immediately after reload
- Best user experience

**Cons:**
- **Very difficult**: Not all Python objects are serializable
  - DataFrame: ✅ Can pickle
  - Trained models: ✅ Can pickle (with limitations)
  - Open file handles: ❌ Cannot pickle
  - Lambda functions: ❌ Cannot pickle
  - Module references: ❌ Cannot pickle
- **Large storage**: DataFrames and models can be huge
- **Security risk**: Unpickling arbitrary Python objects
- **State corruption**: Saved state may become invalid

**Implementation Complexity**: 🔴 High

### Option 2: Per-Notebook Execution Contexts (Moderate)

**Approach**: Each notebook gets its own `ExecutionService` instance

**Architecture:**
```python
class NotebookService:
    def __init__(self):
        self._execution_services = {}  # notebook_id -> ExecutionService

    def get_execution_service(self, notebook_id):
        if notebook_id not in self._execution_services:
            self._execution_services[notebook_id] = ExecutionService()
        return self._execution_services[notebook_id]
```

**Pros:**
- Notebooks don't interfere with each other
- Variables persist while backend is running
- Cleaner architecture

**Cons:**
- Still loses state on backend restart
- More memory usage (one context per notebook)
- Need to manage context lifecycle (cleanup when notebook deleted)

**Implementation Complexity**: 🟡 Moderate

### Option 3: Auto Re-Execute on Load (Recommended - Short Term)

**Approach**: When loading a notebook, automatically re-execute all successfully executed cells

**Implementation:**
```python
def load_notebook(self, notebook_id):
    notebook = self._notebooks[notebook_id]

    # Check if execution context is stale
    if self._is_context_stale(notebook):
        logger.info("Execution context is stale, restoring...")
        self._restore_execution_context(notebook)

    return notebook

def _restore_execution_context(self, notebook):
    """Re-execute all successfully executed cells to restore variables."""
    for cell in notebook.cells:
        if cell.last_result and cell.last_result.status == ExecutionStatus.SUCCESS:
            if cell.code:
                # Re-execute silently
                self.execution_service.execute_code(cell.code, silent=True)
```

**Pros:**
- Simple to implement
- Always accurate (code is re-run, not deserialized)
- No security concerns
- Works for all data types

**Cons:**
- Takes time (need to re-execute all cells)
- May fail if external data changed
- Side effects run again (file writes, API calls, etc.)

**Implementation Complexity**: 🟢 Low

### Option 4: User-Triggered Context Restore (Recommended - Better UX)

**Approach**: Show warning when context is stale, let user decide

**UI Changes:**
```
⚠️ Execution Context Lost

Variables from previous cells are not available because the backend was restarted.

[Re-run All Cells] [Dismiss]

Some variables may be missing: df, model, predictions
```

**Implementation:**
```python
# Add to notebook model
class Notebook:
    execution_context_id: Optional[str] = None  # UUID generated on first execution

# Add to execution service
class ExecutionService:
    context_id: str = str(uuid.uuid4())  # Changes on service restart

# Check in notebook service
def check_context_validity(self, notebook):
    if notebook.execution_context_id != self.execution_service.context_id:
        return {
            "valid": False,
            "message": "Execution context was reset",
            "action": "rerun_all"
        }
    return {"valid": True}
```

**Frontend:**
```tsx
// Show banner when context is stale
{!contextValid && (
  <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4">
    <div className="flex items-center justify-between">
      <div>
        <p className="text-yellow-700">
          ⚠️ Variables from previous cells may not be available.
        </p>
        <p className="text-sm text-yellow-600">
          Backend was restarted. Re-run cells to restore context.
        </p>
      </div>
      <button onClick={rerunAllCells}>
        Re-run All Cells
      </button>
    </div>
  </div>
)}
```

**Pros:**
- User control (no unexpected re-executions)
- Clear feedback about what's happening
- Can choose which cells to re-run
- Simple to implement

**Cons:**
- Extra user action required
- Users may miss the warning

**Implementation Complexity**: 🟢 Low

### Option 5: Smart Context Detection (Recommended - Long Term)

**Approach**: LLM detects missing variables and suggests re-execution

**Implementation:**
```python
# When LLM generates code, check for undefined variables
def generate_and_validate_code(self, prompt, context):
    code = self.llm.generate_code(prompt, context)

    # Parse code for variable usage
    used_vars = extract_variables_from_code(code)
    available_vars = set(self.execution_service.globals_dict.keys())
    missing_vars = used_vars - available_vars

    if missing_vars:
        # LLM suggests which cells to re-run
        suggestion = self.llm.suggest_rerun_cells(missing_vars, notebook)
        return {
            "code": code,
            "warning": f"Variables not found: {missing_vars}",
            "suggestion": suggestion
        }

    return {"code": code, "warning": None}
```

**Pros:**
- Intelligent and proactive
- Only re-runs necessary cells
- Best long-term UX

**Cons:**
- Complex to implement
- Requires code analysis
- LLM may not always detect issues

**Implementation Complexity**: 🔴 High

## Recommended Implementation Plan

### Phase 1: Immediate Fix (Option 4)

1. Add `execution_context_id` to Notebook model
2. Add `context_id` to ExecutionService
3. Check context validity on notebook load
4. Show warning banner in frontend
5. Add "Re-run All Cells" button

**Timeline**: 1-2 hours
**Impact**: Prevents user frustration, makes issue visible

### Phase 2: Better Context Management (Option 2)

1. Implement per-notebook execution services
2. Add context lifecycle management
3. Better memory management

**Timeline**: 4-6 hours
**Impact**: Notebooks don't interfere, better isolation

### Phase 3: Smart Detection (Option 5)

1. Add code analysis for variable detection
2. LLM-powered cell dependency tracking
3. Smart re-execution suggestions

**Timeline**: 8-12 hours
**Impact**: Optimal UX, minimal user friction

## Testing

### Test Case 1: Backend Restart
1. Create notebook with 3 cells computing variables
2. Restart backend
3. Verify warning shows
4. Verify re-run restores context

### Test Case 2: Page Refresh
1. Create notebook with cells
2. Refresh browser
3. Verify context persists (same backend session)

### Test Case 3: Multiple Notebooks
1. Create two notebooks with same variable names
2. Verify they don't interfere (after Phase 2)

## Current Workaround

**For Users:**
1. Keep backend running (don't restart)
2. Don't refresh page unnecessarily
3. If context lost, manually re-run cells from top
4. Use "Run All" feature if available

**For Developers:**
- Document this limitation clearly
- Add to troubleshooting guide
- Consider adding "Checkpoint" feature to save notebook state

## Related Files

- `backend/app/services/execution_service.py` - Execution context management
- `backend/app/services/notebook_service.py` - Notebook loading and context
- `backend/app/services/llm_service.py` - LLM context building
- `backend/app/models/notebook.py` - Notebook data model

## References

- [Jupyter Notebook Kernel Architecture](https://jupyter-client.readthedocs.io/en/stable/kernels.html)
- [Python pickle documentation](https://docs.python.org/3/library/pickle.html)
- [IPython execution model](https://ipython.readthedocs.io/en/stable/interactive/reference.html)

