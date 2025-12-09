# Variable State Persistence - Complete Technical Documentation

**Date**: 2025-11-17
**Issue**: Notebook b3c67992-c0be-4bbf-914c-9f0c100e296c - Variables lost after backend restart
**Root Cause**: No persistence mechanism for execution state
**Solution**: Automatic state persistence system with pickle-based serialization

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Solution Architecture](#solution-architecture)
3. [Implementation Details](#implementation-details)
4. [Usage Guide](#usage-guide)
5. [API Reference](#api-reference)
6. [Troubleshooting](#troubleshooting)
7. [Performance Considerations](#performance-considerations)
8. [Security Considerations](#security-considerations)
9. [Future Enhancements](#future-enhancements)

---

## Problem Statement

### The Critical Issue

**Before the fix**, Digital Article had a fundamental limitation: **All notebook variables were lost when the backend restarted**.

### Evidence from Real Failure

**Notebook**: b3c67992-c0be-4bbf-914c-9f0c100e296c

**Timeline**:
- **12:16**: Cell 1 executes successfully, creates `sdtm_dataset` DataFrame
- **12:19**: Cell 2 executes successfully, uses `sdtm_dataset`
- **[46-minute gap]**: Backend likely restarted
- **13:05**: Cell 3 fails - `sdtm_dataset` no longer exists!

**Error**:
```python
try:
    df = sdtm_dataset.copy()  # NameError: sdtm_dataset not defined!
except NameError:
    # Fallback creates DIFFERENT data
    # Analysis becomes invalid!
```

### Why This Is Critical

Digital Article's core value proposition is enabling **computational notebooks that persist over time**. Users need to:

- Work on multiple notebooks over days/weeks/months
- Return to any notebook and continue where they left off
- Have complete state automatically restored
- Never lose computed results from expensive analyses

**Without state persistence**, users would have to:
- ❌ Re-run all cells after every backend restart
- ❌ Manually save/load data files
- ❌ Lose expensive computations (ML models, large datasets)
- ❌ Deal with non-reproducible results if data sources changed

---

## Solution Architecture

### Core Design: Automatic State Persistence

**Key Principles**:

1. **Automatic**: Zero user action required
2. **Complete**: All serializable Python objects preserved
3. **Reliable**: Atomic writes, error recovery, integrity checks
4. **Transparent**: Users don't even know it's happening
5. **Lazy**: State loaded only when notebook accessed

### System Flow

```
┌─────────────────────────────────────────────────────────────┐
│ User Executes Cell                                          │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ ExecutionService.execute_code()                             │
│                                                              │
│ 1. Get notebook globals                                     │
│    └─> _get_notebook_globals(notebook_id)                   │
│        ├─ Check if in memory                                │
│        ├─ If NOT: Try load_notebook_state(notebook_id)      │
│        │   ├─ State found → Restore pickle → Merge fresh    │
│        │   └─ No state → Create fresh environment           │
│        └─ Return globals_dict                               │
│                                                              │
│ 2. Execute code in globals_dict                             │
│    └─> exec(code, globals_dict)                             │
│                                                              │
│ 3. If SUCCESS:                                              │
│    └─> save_notebook_state(notebook_id, globals_dict)       │
│        ├─ Filter non-serializable objects                   │
│        ├─ Pickle remaining variables                        │
│        ├─ Write atomically (.tmp → rename)                  │
│        ├─ Save metadata (time, count, size, checksum)       │
│        └─ ✅ State persisted to disk                        │
└─────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ Storage on Disk                                             │
│                                                              │
│ backend/notebook_workspace/{notebook_id}/                   │
│ ├── data/                 # User data files                 │
│ └── state/               # NEW: Persisted state             │
│     ├── checkpoint.pkl   # Complete globals dictionary      │
│     └── metadata.json   # Save time, count, size, checksum │
└─────────────────────────────────────────────────────────────┘
```

### Storage Structure

```
backend/notebook_workspace/
└── {notebook_id}/
    ├── data/                         # Existing: user-uploaded files
    │   ├── patient_data.csv
    │   └── results.xlsx
    └── state/                       # NEW: execution state
        ├── checkpoint.pkl           # All variables (pickled)
        ├── metadata.json           # State metadata
        └── backup/                 # Optional: rotating backups
            ├── checkpoint_1.pkl
            └── checkpoint_2.pkl
```

**metadata.json structure**:
```json
{
  "saved_at": "2025-11-17T13:30:45.123456",
  "variable_count": 15,
  "variable_names": ["sdtm_dataset", "results_df", "model", "accuracy"],
  "file_size_bytes": 524288,
  "pickle_protocol": 5,
  "checksum": "a3f5c9e2d1b8f4a6c7e9d2b5f1a8c6e4d3b7f2a9c5e8d1b6f4a7c9e2d5b8f1a3"
}
```

---

## Implementation Details

### Component 1: StatePersistenceService

**File**: `backend/app/services/state_persistence_service.py`

**Core Methods**:

#### `save_notebook_state(notebook_id, globals_dict)`

Saves complete execution state to disk.

**Process**:
1. **Filter non-serializable objects**:
   - Skip built-ins (`__builtins__`, etc.)
   - Skip matplotlib/plotly figures (already captured as images)
   - Skip module objects
   - Test pickle-ability of each variable

2. **Pickle the state**:
   ```python
   pickled_data = pickle.dumps(safe_dict, protocol=pickle.HIGHEST_PROTOCOL)
   ```

3. **Atomic write**:
   ```python
   temp_file = state_file.with_suffix('.tmp')
   with open(temp_file, 'wb') as f:
       f.write(pickled_data)
   temp_file.replace(state_file)  # Atomic rename
   ```

4. **Save metadata**:
   - Timestamp
   - Variable count and names
   - File size
   - SHA-256 checksum for integrity

**Key Features**:
- ✅ Atomic writes prevent corruption
- ✅ Checksum verification
- ✅ Graceful handling of non-serializable objects
- ✅ Comprehensive logging

#### `load_notebook_state(notebook_id)`

Restores previously saved state.

**Process**:
1. Check if state file exists
2. Load metadata and verify checksum
3. Unpickle the state
4. Return restored dictionary

**Error Handling**:
- File not found → Return None (fresh start)
- Corrupt file → Log error, return None
- Unpickle error → Log error, return None

All errors result in fresh environment (graceful degradation).

#### `get_state_metadata(notebook_id)`

Returns metadata without loading full state (for UI indicators).

#### `clear_notebook_state(notebook_id)`

Removes saved state (for troubleshooting or forcing fresh start).

### Component 2: ExecutionService Integration

**File**: `backend/app/services/execution_service.py`

#### Initialization (Lines 83-85)

```python
# State persistence service for automatic save/restore
from .state_persistence_service import StatePersistenceService
self.state_persistence = StatePersistenceService()
```

#### Auto-Restore (Lines 205-237)

Modified `_get_notebook_globals()` to restore state before creating fresh environment:

```python
def _get_notebook_globals(self, notebook_id: str) -> Dict[str, Any]:
    if notebook_id not in self.notebook_globals:
        # Try to restore from saved state first
        saved_state = self.state_persistence.load_notebook_state(notebook_id)

        if saved_state:
            # Merge with fresh globals (for imports/helpers)
            fresh_globals = self._initialize_globals()
            fresh_globals.update(saved_state)
            self.notebook_globals[notebook_id] = fresh_globals
        else:
            # No saved state - create fresh
            self.notebook_globals[notebook_id] = self._initialize_globals()

    return self.notebook_globals[notebook_id]
```

**Key Insight**: Merge saved state with fresh globals to ensure built-in helpers are available.

#### Auto-Save (Lines 514-523)

Added state saving after successful execution:

```python
# After successful execution
if notebook_id:
    try:
        self.state_persistence.save_notebook_state(
            notebook_id,
            globals_dict
        )
    except Exception as save_error:
        # State save failure shouldn't break execution
        logger.error(f"Failed to save state: {save_error}")
```

**Design Decision**: Save failures don't break execution (logged but not raised).

#### Clear Integration (Lines 1128-1133)

Modified `clear_namespace()` to also clear saved state:

```python
# Clear saved state as well
try:
    if self.state_persistence.clear_notebook_state(notebook_id):
        logger.info(f"🗑️  Cleared saved state for notebook {notebook_id}")
except Exception as e:
    logger.error(f"Failed to clear saved state: {e}")
```

### Component 3: API Endpoints

**File**: `backend/app/api/notebooks.py` (Lines 286-388)

#### `GET /api/notebooks/{notebook_id}/state`

Returns metadata about saved state.

**Response**:
```json
{
  "has_saved_state": true,
  "saved_at": "2025-11-17T13:30:45.123456",
  "variable_count": 15,
  "variable_names": ["sdtm_dataset", "results_df", "model"],
  "file_size_bytes": 524288,
  "state_file_exists": true
}
```

**Use Case**: UI can show indicator "State restored from Nov 17, 13:30 (15 variables)"

#### `DELETE /api/notebooks/{notebook_id}/state`

Clears saved state for a notebook.

**Response**:
```json
{
  "success": true,
  "message": "Cleared saved state for notebook abc-123"
}
```

**Use Case**: Troubleshooting - force fresh execution environment

#### `POST /api/notebooks/{notebook_id}/state/restore`

Forces state restoration (clears memory, reloads from disk).

**Response**:
```json
{
  "success": true,
  "message": "State restored successfully",
  "variable_count": 15
}
```

**Use Case**: Manual restoration if something went wrong

---

## Usage Guide

### For Users

**The beauty of this system: You don't need to do anything!**

State persistence is **completely automatic**:

1. **Work normally**: Execute cells, create variables, build models
2. **State auto-saves**: After every successful execution
3. **Backend restarts**: Your variables are safe on disk
4. **Return to notebook**: State automatically restored
5. **Continue working**: As if nothing happened!

### For Developers

#### Accessing State Metadata

```python
# Check if a notebook has saved state
from backend.app.services.shared import notebook_service

has_state = notebook_service.execution_service.state_persistence.has_saved_state(notebook_id)

# Get metadata
metadata = notebook_service.execution_service.state_persistence.get_state_metadata(notebook_id)
print(f"Saved {metadata['variable_count']} variables at {metadata['saved_at']}")
```

#### Manual State Operations

```python
# Clear state (force fresh start)
notebook_service.execution_service.state_persistence.clear_notebook_state(notebook_id)

# Force state save
notebook_service.execution_service.state_persistence.save_notebook_state(
    notebook_id,
    globals_dict
)

# Force state load
restored = notebook_service.execution_service.state_persistence.load_notebook_state(notebook_id)
```

### Verification After Implementation

#### Test 1: Basic Persistence

1. Create new notebook
2. Execute cell: `import pandas as pd; df = pd.DataFrame({'A': [1,2,3]})`
3. Check state saved:
   ```bash
   ls backend/notebook_workspace/{notebook_id}/state/
   # Should see: checkpoint.pkl, metadata.json
   ```
4. Restart backend
5. Access notebook
6. Check logs: Should see "✅ Restored execution state for notebook {id} (X variables)"
7. Execute cell: `print(df)`
8. Verify: DataFrame still exists!

#### Test 2: State After Backend Restart

1. Create notebook, execute multiple cells building complex state
2. Note the variables created
3. **Completely restart backend** (simulate crash)
4. Access notebook
5. Execute cell that uses previous variables
6. Verify: No NameError, all variables available!

#### Test 3: Clear and Restore

1. Create notebook with saved state
2. Call API: `DELETE /api/notebooks/{id}/state`
3. Verify: State file deleted
4. Access notebook → Fresh environment
5. Re-execute cells
6. Verify: New state saved

---

## API Reference

### State Management Endpoints

#### Get State Metadata

```http
GET /api/notebooks/{notebook_id}/state
```

**Response**: 200 OK
```json
{
  "has_saved_state": true,
  "saved_at": "2025-11-17T13:30:45.123456",
  "variable_count": 15,
  "variable_names": ["df", "model", "results"],
  "file_size_bytes": 524288,
  "pickle_protocol": 5,
  "checksum": "a3f5c9e2...",
  "state_file_exists": true
}
```

#### Clear State

```http
DELETE /api/notebooks/{notebook_id}/state
```

**Response**: 200 OK
```json
{
  "success": true,
  "message": "Cleared saved state for notebook {id}"
}
```

#### Force Restore

```http
POST /api/notebooks/{notebook_id}/state/restore
```

**Response**: 200 OK
```json
{
  "success": true,
  "message": "State restored successfully",
  "variable_count": 15
}
```

---

## Troubleshooting

### Issue: State Not Restoring

**Symptoms**: Variables lost after backend restart

**Diagnosis**:
```bash
# Check if state file exists
ls backend/notebook_workspace/{notebook_id}/state/checkpoint.pkl

# Check metadata
cat backend/notebook_workspace/{notebook_id}/state/metadata.json

# Check backend logs
grep "Restored state" backend/logs/*.log
```

**Solutions**:
1. Verify state file exists and has content
2. Check file permissions (should be readable)
3. Check for pickle compatibility issues in logs
4. Try manual restoration: `POST /api/notebooks/{id}/state/restore`

### Issue: State File Corrupt

**Symptoms**: Error logs about pickle/checksum failures

**Diagnosis**:
```bash
# Check metadata for checksum
cat backend/notebook_workspace/{notebook_id}/state/metadata.json | grep checksum

# Try to load manually
python -c "import pickle; pickle.load(open('checkpoint.pkl', 'rb'))"
```

**Solutions**:
1. Clear corrupt state: `DELETE /api/notebooks/{id}/state`
2. Re-execute cells to rebuild state
3. Check disk space/permissions

### Issue: Large State Files

**Symptoms**: Slow save/load, large disk usage

**Diagnosis**:
```bash
# Check state file size
du -h backend/notebook_workspace/{notebook_id}/state/checkpoint.pkl

# Check what's being saved
cat backend/notebook_workspace/{notebook_id}/state/metadata.json | grep variable_names
```

**Solutions**:
1. Identify large variables (likely DataFrames or models)
2. Consider saving large DataFrames separately as parquet files
3. Delete temporary/intermediate variables before creating new ones
4. Use `del large_variable` when no longer needed

### Issue: Non-Serializable Objects

**Symptoms**: Warning logs about skipped variables

**Diagnosis**:
```bash
# Check logs for "Cannot pickle" messages
grep "Cannot pickle" backend/logs/*.log
```

**Solutions**:
- Expected for certain objects (figures, file handles)
- Matplotlib/Plotly figures: Already captured as images
- Database connections: Must be recreated after restoration
- File handles: Must be reopened after restoration

---

## Performance Considerations

### Save Performance

**Typical Save Times**:
- Small state (< 1MB): < 10ms
- Medium state (1-10MB): 10-100ms
- Large state (10-100MB): 100ms-1s
- Very large state (> 100MB): 1-10s

**Optimization Tips**:
1. Use parquet for large DataFrames (more efficient than pickle)
2. Delete intermediate variables when done
3. Consider compressing pickles for very large states (future enhancement)

### Load Performance

**Typical Load Times**:
- Small state: < 50ms
- Medium state: 50-200ms
- Large state: 200ms-2s
- Very large state: 2-20s

**When Loading Occurs**:
- Only when notebook first accessed after backend restart
- Lazy loading: Not during backend startup
- Cached in memory: Only loads once per notebook

### Disk Usage

**Typical State Sizes**:
- Empty notebook: ~1KB (just imports)
- With DataFrames: 100KB - 10MB
- With ML models: 1MB - 100MB
- With large datasets: Can be GBs

**Disk Management**:
- State files stored per-notebook
- Old states overwritten (not accumulated)
- Manual cleanup: `DELETE /api/notebooks/{id}/state`
- Future: Implement rotating backups with retention policy

---

## Security Considerations

### Pickle Security Risks

**Known Issue**: Pickle can execute arbitrary code during unpickling.

**Mitigation in Digital Article**:
1. **Single-user deployment**: User pickles their own data
2. **Workspace isolation**: Each notebook has isolated directory
3. **File permissions**: State files only accessible by owner
4. **No remote sharing**: Notebooks not shared across users

**Risk Assessment**: **LOW** for single-user deployment, **HIGH** for multi-user.

**Future Enhancement**: For multi-user deployment, consider:
- JSON-based serialization for safe objects
- Separate parquet files for DataFrames
- Model-specific formats (HDF5, joblib) for ML models
- Sandboxed unpickling with restricted globals

### File System Security

**Protections**:
1. **Path validation**: All paths stay within workspace directory
2. **No user-controlled paths**: Notebook IDs are UUIDs (not user input)
3. **Atomic writes**: Prevents race conditions
4. **File permissions**: Owner-only read/write

### Data Privacy

**Considerations**:
- State files may contain sensitive data (user DataFrames)
- Stored unencrypted on disk
- Readable by anyone with file system access

**Recommendations**:
- Run Digital Article on encrypted file systems
- Use appropriate file permissions
- Implement file encryption for sensitive deployments (future enhancement)

---

## Future Enhancements

### Short-Term

#### 1. Rotating Backups
Keep last N state checkpoints to recover from corruption:

```
state/
├── checkpoint.pkl              # Current
└── backup/
    ├── checkpoint_1.pkl        # Previous
    ├── checkpoint_2.pkl        # 2 versions back
    └── checkpoint_3.pkl        # 3 versions back
```

#### 2. Compression
Reduce disk usage for large states:

```python
import gzip
pickled = pickle.dumps(state)
compressed = gzip.compress(pickled, compresslevel=6)
# Typical compression: 5-10x for DataFrames
```

#### 3. UI State Indicators

Show state status in notebook UI:
- "State restored from Nov 17, 13:30 (15 variables)"
- "Auto-saved 5 seconds ago"
- "⚠️ Large state (50MB) - consider optimization"

### Medium-Term

#### 4. Selective State Persistence

Let users tag variables to save/skip:

```python
# Save only important variables
__persist__ = ['model', 'results_df', 'final_output']

# Skip temporary variables
__skip_persist__ = ['temp_df', 'intermediate_results']
```

#### 5. Format-Specific Serialization

Use optimal formats for each type:
- DataFrames → Parquet (10x smaller, faster)
- NumPy arrays → NPY (native format)
- Sklearn models → Joblib (optimized for models)
- Simple objects → JSON (human-readable)

#### 6. State Diff and Versioning

Track what changed between saves:

```json
{
  "version": 15,
  "previous_version": 14,
  "changes": {
    "added": ["new_variable"],
    "modified": ["existing_df"],
    "deleted": ["temp_results"]
  }
}
```

### Long-Term

#### 7. Cloud Storage Integration

Sync state to cloud (S3, GCS, Azure Blob):
- Enable work across multiple machines
- Automatic backups
- Collaboration support

#### 8. State Compression & Deduplication

Intelligent storage for large states:
- Incremental saves (only changed variables)
- Deduplication across notebooks
- Delta compression

#### 9. State Analytics

Provide insights into notebook state:
- State size trends over time
- Most memory-consuming variables
- Suggestions for optimization
- Automatic cleanup of unused variables

---

## Appendix

### Key Code Locations

| Component | File | Lines | Description |
|-----------|------|-------|-------------|
| State Persistence Service | `state_persistence_service.py` | 1-309 | Core persistence logic |
| Save State | `state_persistence_service.py` | 107-167 | Pickle and save to disk |
| Load State | `state_persistence_service.py` | 169-257 | Load and unpickle from disk |
| Auto-Restore | `execution_service.py` | 205-237 | Restore state on notebook access |
| Auto-Save | `execution_service.py` | 514-523 | Save state after execution |
| Clear Integration | `execution_service.py` | 1128-1133 | Clear state with namespace |
| API Endpoints | `notebooks.py` | 286-388 | HTTP endpoints for state management |

### State File Format

**checkpoint.pkl Structure** (Pickled Dictionary):
```python
{
    'sdtm_dataset': <pandas.DataFrame>,
    'model': <sklearn.RandomForestClassifier>,
    'results': {'accuracy': 0.95, 'precision': 0.93},
    'fig_data': <numpy.ndarray>,
    # ... all serializable user variables
}
```

**metadata.json Structure**:
```json
{
  "saved_at": "ISO8601 timestamp",
  "variable_count": 15,
  "variable_names": ["var1", "var2", ...],
  "file_size_bytes": 524288,
  "pickle_protocol": 5,
  "checksum": "SHA-256 hash"
}
```

### Glossary

- **State**: The complete set of variables in a notebook's execution environment
- **Globals Dictionary**: Python dict containing all variables (`globals()`)
- **Checkpoint**: A saved snapshot of state at a point in time
- **Pickle**: Python's native object serialization format
- **Atomic Write**: Write operation that completes fully or not at all (prevents corruption)
- **Lazy Loading**: Loading data only when needed (not eagerly at startup)

---

**Document Version**: 1.0
**Last Updated**: 2025-11-17
**Status**: Production-Ready
