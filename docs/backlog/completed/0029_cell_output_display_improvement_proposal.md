# Backlog Item (Historical; migrated from legacy planning)

## Title
Cell Output Display Improvement Proposal

## Backlog ID
0029

## Priority
- **P2 (historical)**: migrated record from the legacy `docs/planning/` folder to keep governance artifacts in one system.

## Date / Time
Unknown (historical; migrated 2026-01-31)

## Short Summary
This file preserves a historical planning/proposal document that previously lived under `docs/backlog/completed/0029_cell_output_display_improvement_proposal.md`. It has been migrated to `docs/backlog/completed/` so older design artifacts live under the backlog governance system.

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
- Legacy source: `docs/backlog/completed/0029_cell_output_display_improvement_proposal.md` (removed after migration)
- Canonical docs: [`docs/overview.md`](../../overview.md), [`docs/architecture.md`](../../architecture.md)

## Full Report (legacy planning content)

# Cell Output Display Improvement Proposal

> **Status**: Planning / exploratory note.  
> This document discusses output-capture behavior in `ExecutionService` and is not a user-facing guide.  
> For current execution/output behavior, see `docs/dive_ins/execution_service.md`.

## Current Behavior (Already Correct!)

Your system **already works correctly** - it only shows new or modified outputs per cell:

### Backend Logic (`execution_service.py:415-422`)
```python
# Only capture DataFrames that are new or have been modified
is_new_variable = pre_execution_vars is None or name not in pre_execution_vars
is_modified_dataframe = (
    pre_execution_dataframes is not None and
    name in pre_execution_dataframes and
    not obj.equals(pre_execution_dataframes[name])
)

if is_new_variable or is_modified_dataframe:
    # Capture this DataFrame
```

### Frontend Logic (`ResultPanel.tsx:137-139`)
```typescript
{result.tables.map((table, index) => (
  <TableDisplay key={index} table={table} />
))}
```

Each cell **only** displays outputs from its own `last_result`.

---

## Why It Might Feel "Cumulative"

### Scenario 1: Same Variable Name Across Cells
```python
# Cell 1
df = pd.read_csv('data/file.csv')
# Shows: df (100 rows × 5 cols)

# Cell 2
df = df[df['age'] > 30]
# Shows: df (50 rows × 5 cols) ← Modified, so shown again

# Cell 3
df = df.sort_values('name')
# Shows: df (50 rows × 5 cols) ← Modified again, so shown again
```

**This is correct behavior!** Each cell modifies `df`, so each cell should show the result.

### Scenario 2: Creating Multiple DataFrames
```python
# Cell 1
df1 = pd.read_csv('data/file1.csv')
# Shows: df1

# Cell 2
df2 = pd.read_csv('data/file2.csv')
# Shows: df2 (not df1)

# Cell 3
df3 = pd.merge(df1, df2)
# Shows: df3 (not df1 or df2)
```

**This is also correct!** Only newly created DataFrames are shown.

---

## Potential UI Enhancement: Visual Indicators

If you want to make it **more obvious** which outputs are new vs modified, here are options:

### Option 1: Add Badges to Table Headers
```tsx
<div className="flex items-center justify-between mb-2">
  <span className="font-medium">{table.name}</span>
  {table.is_new ? (
    <span className="px-2 py-1 text-xs bg-green-100 text-green-800 rounded">
      NEW
    </span>
  ) : (
    <span className="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">
      MODIFIED
    </span>
  )}
</div>
```

**Requires backend change**: Add `is_new` field to table metadata.

### Option 2: Collapsible "Previous Context" Section
Show a **summary** of available variables without full data:

```tsx
{/* Available Variables (collapsed by default) */}
<details className="mb-4">
  <summary className="cursor-pointer text-sm text-gray-600">
    📊 Available Variables (click to expand)
  </summary>
  <div className="mt-2 p-3 bg-gray-50 rounded">
    {availableVariables.map(v => (
      <div key={v.name} className="text-xs">
        {v.name}: {v.type} {v.shape}
      </summary>
    ))}
  </div>
</details>

{/* Only NEW/MODIFIED outputs shown by default */}
```

### Option 3: Inline Context Indicator
```tsx
{table.was_modified && (
  <div className="text-xs text-gray-500 mb-1">
    ← Modified from previous value (shape was {table.previous_shape})
  </div>
)}
```

### Option 4: Variable Dependency Graph
Show which variables were **used** vs **created**:

```
Cell 3 Execution:
  📥 Used: df1, df2
  📤 Created: df3 ← Only this is shown in output
```

---

## Recommendation: NO CHANGE NEEDED

**Your current implementation is already optimal!** Here's why:

### ✅ Current Behavior is Jupyter-like
- Variables persist across cells (expected)
- Only new/modified outputs shown (expected)
- Clean, uncluttered display (expected)

### ✅ Follows Best Practices
- Users can see the result of their current operation
- Previous variables are available but not visually noisy
- Same mental model as Jupyter notebooks

### ✅ Already Has Variable Inspection
Your system likely has:
- Variable inspector (can check what's in memory)
- `print()` statements work for exploring data
- Each cell shows what it changed

---

## If You Still Want Changes...

### Test Current Behavior First

Create a test notebook:
```python
# Cell 1
import pandas as pd
df = pd.DataFrame({'a': [1, 2, 3]})

# Cell 2
df_new = df.copy()
df_new['b'] = [4, 5, 6]

# Cell 3
df_modified = df_new * 2

# Cell 4
print("This cell doesn't create tables")
```

**Expected output**:
- Cell 1: Shows `df`
- Cell 2: Shows `df_new` (NOT df)
- Cell 3: Shows `df_modified` (NOT df or df_new)
- Cell 4: Shows stdout only

If this is NOT what you're seeing, there's a bug.
If this IS what you're seeing, the system works correctly!

---

## Conclusion

**The system already implements per-cell output display correctly.**

If it feels cumulative, it's because:
1. You're reusing variable names (intentional)
2. Multiple cells modify the same data (expected workflow)
3. Each modification is significant enough to show (good!)

**Recommendation**: Keep current behavior. It's clean, correct, and Jupyter-compatible.

If you want visual enhancements, Option 1 (badges) is simplest and requires minimal changes.

