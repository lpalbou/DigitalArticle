# Fix: Duplicate Figures from display()

**Date**: 2025-12-04
**Bug**: Figure 1 shown twice in notebook d63aa801-d64a-4e99-ad7e-1f6b7dcfec29
**Status**: ✅ FIXED

---

## Problem

User's code:
```python
fig = plt.figure(figsize=(20, 16))
# ... create subplots ...
display(fig, "Figure 1: TNBC Clinical Trial Dashboard")
```

**Result**: Figure 1 appeared **TWICE** in the output

---

## Root Cause

**Execution flow**:
1. Code calls `display(fig, "Figure 1: ...")`
2. Figure is captured from `display.results` → added to plots
3. **Figure NOT closed** → remains in `plt.get_fignums()`
4. `_capture_plots()` auto-captures ALL open figures
5. **Same figure captured AGAIN** → duplicate!

**Location**: `backend/app/services/execution_service.py`

- Line 561: Capture from `display()` → adds to result.plots
- Line 567: `_capture_plots()` → captures SAME figure again
- Line 1108-1124: Figure converted but NOT closed

---

## The Fix

**File**: `backend/app/services/execution_service.py` lines 1119-1125

Added `plt.close(obj)` after capturing matplotlib figure:

```python
# After converting figure to base64
buffer.close()

# Close the figure to prevent auto-capture duplication
try:
    plt.close(obj)  # ← FIX!
    logger.debug(f"Closed matplotlib figure after display: {label}")
except Exception as close_err:
    logger.warning(f"Could not close matplotlib figure: {close_err}")
```

---

## Impact

### Before (Broken)
```
display(fig, "Figure 1")
↓
Results:
- Figure 1 (from display)
- Figure 1 (from auto-capture)  ← DUPLICATE!
```

### After (Fixed)
```
display(fig, "Figure 1")
↓
Figure closed after capture
↓
Results:
- Figure 1 (from display)  ← ONLY ONE!
```

---

## Why This Works

1. `display(fig, "Figure 1")` captures and converts figure
2. **`plt.close(fig)` removes figure from matplotlib's open figures list**
3. `_capture_plots()` only captures remaining open figures
4. **No duplication!**

---

## Testing

**Test Case 1**: Explicit display
```python
fig, ax = plt.subplots()
ax.plot([1, 2, 3])
display(fig, "Figure 1: Test")
```
**Expected**: Figure 1 appears ONCE

**Test Case 2**: Multiple figures
```python
fig1, ax1 = plt.subplots()
ax1.plot([1, 2, 3])
display(fig1, "Figure 1: Plot A")

fig2, ax2 = plt.subplots()
ax2.plot([4, 5, 6])
display(fig2, "Figure 2: Plot B")
```
**Expected**: Figure 1 and Figure 2, each appearing ONCE

**Test Case 3**: Mixed display + auto-capture
```python
# Explicit
fig1, ax1 = plt.subplots()
ax1.plot([1, 2, 3])
display(fig1, "Figure 1: Explicit")

# Auto (no display call)
fig2, ax2 = plt.subplots()
ax2.plot([4, 5, 6])
# No display() - should be auto-captured
```
**Expected**: Figure 1 (labeled) + Figure 2 (unlabeled auto-capture)

---

## Files Modified

| File | Lines | Change |
|------|-------|--------|
| `backend/app/services/execution_service.py` | 1119-1125 | Add plt.close() after figure capture |

**Total**: 1 file, 7 lines added

---

## Notes

- **Fail-safe**: Try-except around `plt.close()` - won't break if close fails
- **Backward compatible**: Doesn't affect auto-captured figures (those without display())
- **Clean**: Closes figures after use, prevents memory leaks
- **Logging**: Debug log when figure closed for troubleshooting

---

## Conclusion

**Simple, clean fix**: Close matplotlib figures after capturing them from `display()` to prevent duplicate auto-capture.

**User impact**: No more duplicate figures in output!
