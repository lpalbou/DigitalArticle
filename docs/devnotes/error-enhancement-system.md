# Error Enhancement System

## Overview

The Error Enhancement System provides domain-specific, actionable guidance to the LLM during auto-retry cycles, improving its ability to fix errors in generated code.

Enhanced error messages provide mathematical explanations, fix strategies, and code examples, containing approximately 19.5x more detail than raw error messages.

**🚨 IMPORTANT**: This system is the **SINGLE SOURCE OF TRUTH** for all error handling in Digital Article. See `docs/error-handling.md` for consolidation guidelines.

## The Problem

When the LLM generates code that fails during execution, the auto-retry mechanism would receive only the raw Python error:

```
ValueError: num must be an integer with 1 <= num <= 12, not 13
```

This minimal context often led to:
- Multiple retry attempts needed
- Same errors repeated
- Failure to understand library-specific constraints
- Poor fix success rate

## The Solution

The Error Enhancement System analyzes errors and provides rich, domain-specific context:

```
================================================================================
MATPLOTLIB SUBPLOT GRID CONSTRAINT VIOLATED

Original Error: num must be an integer with 1 <= num <= 12, not 13

EXPLANATION:
Matplotlib subplot grids have a fundamental mathematical constraint:
  subplot_index must be ≤ (nrows × ncols)

You attempted to create subplot #13 in a grid that only has 12 positions.
This is NOT a matplotlib limitation - it's a mathematical constraint.

FIX OPTIONS:
1. Reduce number of subplots to 12
2. Increase grid size to 3x5 (15 positions) or 4x4 (16 positions)
3. Fix loop range: for i in range(1, 13) instead of range(1, 14)

DETECTED SUBPLOT CALLS:
  - plt.subplot(3, 4, i)
================================================================================
```

## Architecture

### Core Component: ErrorAnalyzer

**Location**: `backend/app/services/error_analyzer.py`

```python
class ErrorAnalyzer:
    """
    Analyzes Python execution errors and provides enhanced context.

    Plugin-style architecture with specialized analyzers for:
    - Matplotlib errors (subplot constraints, figure management)
    - Pandas errors (KeyError, merge errors)
    - File I/O errors (missing data/ prefix)
    - NumPy errors (shape mismatches)
    - Import errors (unavailable modules)
    - Generic Python errors (TypeError, IndexError, etc.)
    """
```

### Integration Points

1. **LLM Service** (`backend/app/services/llm_service.py`)
   - `suggest_improvements()` method enhanced with `_enhance_error_context()`
   - Automatically analyzes errors before passing to LLM

2. **Notebook Service** (`backend/app/services/notebook_service.py`)
   - Auto-retry loop now calls `suggest_improvements()` with full error context
   - Passes `error_type`, `error_message`, and `traceback` to LLM service

### Data Flow

```
Code Execution Error
    ↓
ExecutionService captures:
  - error_type (ValueError, KeyError, etc.)
  - error_message
  - full traceback
  - failed code
    ↓
NotebookService auto-retry detects error
    ↓
Calls LLMService.suggest_improvements(
    prompt=original_prompt,
    code=failed_code,
    error_message=error_message,
    error_type=error_type,
    traceback=traceback
)
    ↓
LLMService._enhance_error_context()
    ↓
ErrorAnalyzer.analyze_error()
  - Tries each specialized analyzer in order
  - First match wins (matplotlib → pandas → file I/O → ...)
  - Falls back to generic context if no match
    ↓
ErrorAnalyzer.format_for_llm()
  - Creates structured, LLM-friendly output
  - Includes error analysis, guidance, suggestions
    ↓
Enhanced context passed to LLM
    ↓
LLM generates fixed code with better understanding
```

## Specialized Analyzers

### 1. Matplotlib Subplot Analyzer

**Detects**: `ValueError: num must be an integer with 1 <= num <= 12, not X`

**Provides**:
- Mathematical explanation of nrows × ncols constraint
- Extraction of attempted position and grid size
- Suggestions for alternative grid sizes
- Detection of loop range errors
- Examples of correct code patterns

**Example Enhancement**:
```
MATHEMATICAL CONSTRAINT: You tried to create subplot position 13, but the grid only has 12 positions.

When calling plt.subplot(nrows, ncols, index):
  - Total positions available = nrows × ncols
  - Valid index range = 1 to (nrows × ncols)

FIX OPTIONS:
1. Reduce subplots to 12
2. Increase grid size:
   - plt.subplot(3, 5, ...) gives 15 positions
   - plt.subplot(4, 4, ...) gives 16 positions
3. Fix loop: range(1, nrows*ncols+1) instead of range(1, 14)
```

### 2. Pandas KeyError Analyzer

**Detects**: `KeyError: 'column_name'` in DataFrame operations

**Provides**:
- Column name that's missing
- Debugging commands (print df.columns)
- Common causes (typos, case sensitivity, whitespace)
- Safe access patterns (df.get())

### 3. File Not Found Analyzer

**Detects**: `FileNotFoundError` for data files

**Provides**:
- **Critical**: Emphasis on `data/` directory requirement
- Extraction of attempted filenames
- Correct vs incorrect path patterns
- Examples: `'data/file.csv'` not `'file.csv'`

**Example Enhancement**:
```
FILE ACCESS ERROR - DATA DIRECTORY REQUIRED

All data files MUST be accessed via 'data/' prefix:
  ✓ CORRECT: pd.read_csv('data/gene_expression.csv')
  ✗ WRONG:   pd.read_csv('gene_expression.csv')

You attempted: 'myfile.csv'
Fix: Change to 'data/myfile.csv'
```

### 4. Import Error Analyzer

**Detects**: `ModuleNotFoundError`, `ImportError`

**Provides**:
- List of available libraries
- Suggested alternatives
- Common replacements (e.g., use sklearn instead of tensorflow)

### 5. NumPy Shape Analyzer

**Detects**: Shape mismatch and broadcasting errors

**Provides**:
- Explanation of broadcasting rules
- Debugging commands (print shapes)
- Reshape suggestions

### 6. Generic Analyzers

For TypeError, IndexError, ValueError:
- General debugging steps
- Type checking commands
- Common patterns to check

## Design Principles

### 1. General-Purpose, No Artificial Constraints

**Rule**: Never restrict valid code, only add helpful context

The system:
- ✅ Explains library constraints (matplotlib grid math)
- ✅ Provides multiple fix options
- ✅ Shows correct patterns
- ❌ Never prevents valid operations
- ❌ Never modifies code execution
- ❌ Never changes library behavior

### 2. Robust and Fault-Tolerant

**Rule**: System must never crash, even with malformed input

```python
try:
    context = analyzer.analyze_error(...)
except Exception as e:
    # Fall back to raw error message
    return f"{error_type}: {error_message}\n{traceback}"
```

**Handles**:
- Empty error messages
- Missing traceback
- Binary garbage in strings
- Unicode characters
- Very long code (10,000+ lines)
- Null/None values

### 3. Ordered Analyzer Priority

Analyzers run in order from **most specific to most generic**:

1. Matplotlib subplot (highly specific pattern)
2. Matplotlib figure errors
3. File not found (data/ context specific)
4. Pandas KeyError
5. Pandas merge
6. NumPy shape
7. Import errors
8. TypeError
9. IndexError
10. ValueError (catch-all)
11. Generic (fallback)

**First match wins** - ensures most relevant guidance is provided.

### 4. LLM-Friendly Formatting

Output structure optimized for LLM comprehension:

```
================================================================================
ERROR ANALYSIS AND FIX GUIDANCE
================================================================================

[Enhanced explanation with WHY, WHAT, HOW]

================================================================================
DETAILED GUIDANCE FOR FIXING THIS ERROR
================================================================================

[Numbered, actionable steps with examples]

================================================================================
ORIGINAL ERROR MESSAGE
================================================================================

[Raw error for reference]

[Optional: RELEVANT DOCUMENTATION link]
```

## Testing

### Test Coverage: 21 Tests, 100% Pass Rate

**Location**: `tests/error_analyzer/`

#### 1. Matplotlib Error Tests (`test_matplotlib_errors.py`)

- `test_subplot_grid_constraint_basic` - Basic detection
- `test_subplot_grid_suggestions_provided` - Grid size suggestions
- `test_subplot_call_extraction` - Code parsing
- `test_grid_size_suggestions` - Algorithm correctness
- `test_formatted_output_for_llm` - LLM-friendly format
- `test_subplot_error_vs_other_valueerror` - Specificity
- `test_figure_error_detection` - Figure management errors

#### 2. Robustness Tests

- `test_empty_error_message` - Handles empty input
- `test_none_values` - Null safety
- `test_analyzer_exception_handling` - Binary garbage
- `test_very_long_code` - 10,000 line code
- `test_unicode_in_error` - Unicode handling

#### 3. Pandas Error Tests (`test_pandas_errors.py`)

- `test_pandas_column_not_found` - KeyError detection
- `test_pandas_merge_error` - Merge guidance
- `test_missing_data_prefix` - File path guidance
- `test_correct_data_path_in_suggestions` - Path examples
- `test_module_not_found` - Import error handling

#### 4. Real Scenario Tests (`test_real_scenario.py`)

- `test_matplotlib_subplot_error_real_scenario` - Your actual error
- `test_enhanced_context_compared_to_raw_error` - Before/after comparison
- `test_error_enhancement_is_robust` - Partial information
- `test_formatted_output_helps_llm_understand_fix` - Actionability

### Run Tests

```bash
source .venv/bin/activate
pytest tests/error_analyzer/ -v
```

**Expected**: 21 passed

## Impact Metrics

### Before Enhancement

```
Error passed to LLM:
ValueError: num must be an integer with 1 <= num <= 12, not 13

Length: 112 characters
```

### After Enhancement

```
[Full enhanced context with explanations and guidance]

Length: 2,182 characters
Enhancement: 19.5x more detailed
```

### What's Included Now

1. ✅ **Mathematical explanation** of constraint
2. ✅ **Specific fix suggestions** (3-5 options)
3. ✅ **Alternative grid sizes** for matplotlib
4. ✅ **Common error patterns** to avoid
5. ✅ **Code examples** (correct vs incorrect)
6. ✅ **Relevant documentation** links
7. ✅ **Detected code patterns** in failure

## Extension Guide

### Adding a New Analyzer

1. **Create analyzer method** in `ErrorAnalyzer` class:

```python
def _analyze_my_library_error(
    self,
    error_message: str,
    error_type: str,
    traceback: str,
    code: str
) -> Optional[ErrorContext]:
    """Analyze my library-specific errors."""

    # Detection logic
    if error_type != "SpecificError":
        return None

    if "my_library" not in traceback:
        return None

    # Analysis logic
    suggestions = [
        "MY LIBRARY ERROR DETECTED",
        "",
        "Causes:",
        "1. ...",
        "",
        "Solutions:",
        "1. ...",
    ]

    enhanced_message = f"My library error: {error_message}"

    return ErrorContext(
        original_error=error_message,
        error_type=error_type,
        enhanced_message=enhanced_message,
        suggestions=suggestions,
        relevant_docs="https://docs.example.com"
    )
```

2. **Register analyzer** in `__init__`:

```python
self.analyzers = [
    self._analyze_matplotlib_subplot_error,
    self._analyze_my_library_error,  # Add here
    # ... other analyzers
    self._analyze_value_error,  # Generic should be last
]
```

3. **Write tests**:

```python
def test_my_library_error():
    analyzer = ErrorAnalyzer()
    context = analyzer.analyze_error(
        error_message="...",
        error_type="SpecificError",
        traceback="...",
        code="..."
    )
    assert "my library" in context.enhanced_message.lower()
```

### Analyzer Best Practices

1. **Be specific** - Only match errors you can help with
2. **Return None** early if not your domain
3. **Provide actionable fixes** - Not just explanations
4. **Include examples** - Show correct code patterns
5. **Explain WHY** - Not just WHAT
6. **Multiple options** - Give 3-5 fix strategies
7. **Test robustness** - Handle edge cases gracefully

## Future Enhancements

### Near Term

- **Plotly errors** - Interactive plot issues
- **Seaborn errors** - Statistical plot guidance
- **Scikit-learn errors** - ML pipeline errors
- **Custom error patterns** - User-defined analyzers

### Long Term

- **Learning from fixes** - Track which suggestions work
- **Context-aware suggestions** - Use notebook history
- **Multi-error analysis** - Handle cascading errors
- **Severity ranking** - Prioritize critical issues
- **Auto-fix suggestions** - Provide code patches

## Conclusion

The Error Enhancement System transforms the auto-retry mechanism from a "blind retry" to an "intelligent debugging assistant."

Key benefits include:
1. 19.5x more detailed error context for LLM
2. Domain-specific guidance (matplotlib, pandas, etc.)
3. No artificial constraints - explains without restricting valid operations
4. Robust handling of edge cases
5. Extensible architecture for adding new analyzers
6. Comprehensive test coverage (21 tests, 100% pass rate)
7. Transparent error reporting to users

This results in higher auto-retry success rates, fewer wasted LLM calls, and improved user experience.

---

*For questions or contributions, see the main README.md or open an issue.*
