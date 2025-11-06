# Error Handling System

## Overview

This document describes Digital Article's intelligent error handling and auto-retry system. The system provides automatic error analysis, enhanced LLM context, and code fixes to minimize user interruption during data analysis.

**Related Documentation:**
- [Architecture Overview](architecture.md) - Overall system design
- [Error Enhancement System](devnotes/error-enhancement-system.md) - Implementation details
- [Getting Started](getting-started.md) - User-facing error recovery features

This document defines the **single source of truth** for error handling architecture to prevent parallel implementations and ensure consistency.

## User Experience

From a user perspective, Digital Article's error handling provides:

- **Automatic Error Recovery**: When code fails, the system automatically attempts to fix errors up to 5 times
- **Intelligent Analysis**: Specialized analyzers provide domain-specific guidance for pandas, matplotlib, numpy, and other libraries
- **Transparent Process**: Users see "correcting code x/5" progress indicators during auto-retry
- **Minimal Interruption**: Most common errors are resolved without user intervention
- **Educational Value**: When manual intervention is needed, users receive enhanced error messages with specific suggestions

## Developer Architecture

### Core Principle

**ALL ERROR HANDLING MUST GO THROUGH THE ErrorAnalyzer SYSTEM**

## Architecture

### Primary Error Handling Flow (MANDATORY)

```
Error Occurs
    ↓
ExecutionService captures:
  - error_type, error_message, traceback, code
    ↓
NotebookService auto-retry calls:
  LLMService.suggest_improvements()
    ↓
LLMService._enhance_error_context()
    ↓
ErrorAnalyzer.analyze_error()
  - Tries specialized analyzers in order
  - Returns ErrorContext with suggestions
    ↓
ErrorAnalyzer.format_for_llm()
  - Creates structured LLM prompt
    ↓
LLM generates fixed code with enhanced context
```

### Components

#### 1. ErrorAnalyzer (PRIMARY - AUTHORITATIVE)
**Location**: `backend/app/services/error_analyzer.py`
**Role**: Single source of truth for all error analysis
**Features**:
- Specialized analyzers for different error types
- Domain-specific guidance (pandas, matplotlib, numpy, etc.)
- Structured suggestions and documentation links
- Extensible plugin architecture

#### 2. LLMService.suggest_improvements() (INTEGRATION POINT)
**Location**: `backend/app/services/llm_service.py`
**Role**: Routes ALL error fixing through ErrorAnalyzer
**Responsibility**: 
- MUST call `_enhance_error_context()` for ALL errors
- Formats enhanced context for LLM consumption
- Handles LLM communication

#### 3. Basic Error Fixes (FALLBACK ONLY)
**Location**: `backend/app/services/notebook_service.py._apply_basic_error_fixes()`
**Role**: Emergency fallback when LLM service fails
**Usage**: ONLY when `suggest_improvements()` throws exception
**Scope**: Simple programmatic fixes only

## Rules and Constraints

### ✅ REQUIRED PATTERNS

1. **All error analysis MUST go through ErrorAnalyzer**
   ```python
   # CORRECT
   enhanced_context = self.llm_service.suggest_improvements(
       prompt=prompt,
       code=code,
       error_message=error_message,
       error_type=error_type,
       traceback=traceback
   )
   ```

2. **New error types MUST be added to ErrorAnalyzer**
   ```python
   # Add to ErrorAnalyzer.__init__()
   self.analyzers = [
       self._analyze_new_error_type,  # NEW analyzer here
       # ... existing analyzers
   ]
   ```

3. **All LLM error fixing MUST use suggest_improvements()**
   ```python
   # CORRECT - goes through ErrorAnalyzer
   fixed_code = llm_service.suggest_improvements(...)
   
   # WRONG - bypasses error analysis
   fixed_code = llm_service.llm.generate(raw_prompt)
   ```

### ❌ FORBIDDEN PATTERNS

1. **Direct LLM calls for error fixing**
   ```python
   # WRONG - bypasses ErrorAnalyzer
   response = llm.generate(f"Fix this error: {error_message}")
   ```

2. **Parallel error analysis implementations**
   ```python
   # WRONG - duplicates ErrorAnalyzer logic
   if "pandas" in error_message:
       # custom pandas handling here
   ```

3. **Multiple fallback mechanisms**
   ```python
   # WRONG - creates maintenance burden
   def another_basic_fix_function():
       # duplicates _apply_basic_error_fixes
   ```

## Current Implementation Status

### ✅ COMPLIANT
- `NotebookService.execute_cell()` auto-retry loop
- `LLMService.suggest_improvements()` 
- `ErrorAnalyzer` system with specialized analyzers

### ⚠️ NEEDS CONSOLIDATION
- `ai_code_fix.py` - Should route through `suggest_improvements()`
- `_apply_basic_error_fixes()` - Should be minimal fallback only

### 🔧 REQUIRED CHANGES

#### 1. Fix ai_code_fix.py
**Current**: Direct LLM call without error analysis
**Required**: Route through `suggest_improvements()`

```python
# BEFORE (in ai_code_fix.py)
response = llm_service.llm.generate(fix_prompt, max_tokens=2000)

# AFTER
if error_context_available:
    fixed_code = llm_service.suggest_improvements(
        prompt=user_request,
        code=current_code,
        error_message=inferred_error,
        error_type=inferred_type,
        traceback=""
    )
else:
    # For non-error fixes, direct call is acceptable
    response = llm_service.llm.generate(fix_prompt, max_tokens=2000)
```

#### 2. Minimize Basic Error Fixes
**Current**: Complex logic duplicating ErrorAnalyzer
**Required**: Simple fallback only

```python
def _apply_basic_error_fixes(self, code: str, error_message: str, error_type: str) -> Optional[str]:
    """
    EMERGENCY FALLBACK ONLY - when LLM service completely fails.
    
    This should contain ONLY simple, safe transformations.
    All sophisticated error analysis belongs in ErrorAnalyzer.
    """
    if not error_message or not code:
        return None
    
    # ONLY simple, safe fixes here
    if error_type == "FileNotFoundError" and "data/" not in code:
        return f"# Auto-fix: Added data/ prefix\n{code.replace('\"', '\"data/')}"
    
    # DO NOT duplicate ErrorAnalyzer logic here
    return None
```

## Adding New Error Types

### Step 1: Add Analyzer to ErrorAnalyzer
```python
# In error_analyzer.py
def _analyze_new_error_type(self, error_message, error_type, traceback, code):
    if error_type != "NewErrorType":
        return None
    
    # Analysis logic here
    return ErrorContext(
        original_error=error_message,
        error_type=error_type,
        enhanced_message="Enhanced explanation",
        suggestions=["Suggestion 1", "Suggestion 2"]
    )

# Add to __init__
self.analyzers = [
    self._analyze_new_error_type,  # Add here
    # ... existing analyzers
]
```

### Step 2: Test Integration
```python
# Test that it flows through the system
result = llm_service.suggest_improvements(
    prompt="test",
    code="test code",
    error_message="NewErrorType: test error",
    error_type="NewErrorType",
    traceback="test traceback"
)
```

## Monitoring and Maintenance

### Key Metrics
- Error analysis coverage (% of errors handled by specialized analyzers)
- Auto-retry success rate after error enhancement
- Fallback usage frequency (should be minimal)

### Warning Signs
- High fallback usage → Need more specialized analyzers
- Duplicate error handling logic → Consolidation needed
- Direct LLM calls for errors → Architecture violation

## Migration Guide

### For Existing Code
1. Replace direct LLM error fixing with `suggest_improvements()`
2. Move sophisticated logic from fallbacks to ErrorAnalyzer
3. Keep fallbacks minimal and safe

### For New Features
1. Always use `suggest_improvements()` for error fixing
2. Add specialized analyzers for new error types
3. Never bypass the ErrorAnalyzer system

---

**Remember**: The goal is to have ONE authoritative system for error analysis that provides consistent, high-quality guidance to the LLM, making our auto-retry system more effective and maintainable.








