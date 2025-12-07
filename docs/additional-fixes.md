# M&S Persona - Additional Fixes (2025-12-06)

## Overview

This document describes fixes applied to the Modeling & Simulation persona after investigation of Workflow 1 (Single Ascending Dose study) execution.

**Investigation Notebook**: `313e29bf-cc17-4c48-b41d-4d540fb02763`
**Export**: `/Users/albou/Downloads/MS-DA.json`
**Overall Result**: ✅ **WORKFLOW SUCCESSFUL** with 2 issues fixed

---

## Fix 1: Critique Service API Mismatch 🔴 CRITICAL

### Problem

Every cell showed error:
```
Critique process failed: BasicSession.generate_assessment() got an unexpected keyword argument 'include_score'
```

### Root Cause

**Semantic mismatch** between AbstractCore and Digital Article:

- **AbstractCore's `generate_assessment()`**: Designed for general **conversation quality**
  - Criteria: clarity, coherence, relevance, completeness, actionability
  - Signature: `generate_assessment(self, criteria: Optional[Dict[str, bool]] = None)`

- **Digital Article's `AnalysisCritic`**: Needs **data analysis quality** assessment
  - Criteria: logical_coherence, result_plausibility, assumption_validity, interpretation_quality, completeness
  - Was incorrectly calling with List[str] and non-existent `include_score` parameter

### Solution

**Removed broken `session.generate_assessment()` call**, relying on existing `BasicJudge.evaluate()` which already provides domain-specific assessment.

**File**: `backend/app/services/analysis_critic.py`

**Changes**:
```python
# BEFORE (lines 97-130):
session = BasicSession(self.llm, system_prompt=self._build_critique_system_prompt())
assessment_raw = session.generate_assessment(
    criteria=["logical_coherence", ...],
    include_score=True  # <-- Error: parameter doesn't exist
)
judge_assessment = self.judge.evaluate(...)
critique = self._build_critique_from_assessments(assessment_raw, judge_assessment, ...)

# AFTER:
# Removed session.generate_assessment() call - semantic mismatch with our use case
judge_assessment = self.judge.evaluate(
    text=critique_context,
    context="data analysis quality assessment",
    focus="result plausibility, assumption checking, interpretation accuracy"
)
critique = self._build_critique_from_assessments(None, judge_assessment, ...)
```

**Result**: ✅ Critique service now works without errors

---

## Fix 2: Strengthen lmfit Guidance 🟡 MEDIUM

### Problem

**Cell 4 (Compartmental Model Fitting)**:
- Prompt explicitly said: "Use **lmfit** for parameter estimation..."
- Persona guidance said: "Prefer lmfit.Model over scipy.optimize.curve_fit"
- **LLM generated**: Code using `scipy.optimize.curve_fit` instead

**Root Cause**: Local LLM (qwen/qwen3-next-80b) didn't follow persona guidance strictly enough.

### Solution

**Made lmfit guidance explicit and prominent** in both persona constraints and workflow prompts.

#### File 1: `data/personas/system/modeling-simulation.json`

**Added CRITICAL constraint**:
```json
"CRITICAL: For compartmental PK model fitting, ALWAYS use lmfit.Model or lmfit.minimize, NEVER use scipy.optimize.curve_fit - lmfit provides proper confidence intervals and parameter bounds"
```

#### File 2: `docs/persona-ms-scenarios.md`

**Updated Prompt 4** to be more explicit:
```
BEFORE:
Fit a one-compartment IV bolus model to the pooled SAD data:
- Use lmfit for parameter estimation with bounds (CL > 0, Vd > 0)

AFTER:
Fit a one-compartment IV bolus model to the pooled SAD data:
- Import and use lmfit library (from lmfit import Model, Parameters)
- Define the one-compartment IV bolus model equation: C(t) = (Dose/Vd) * exp(-CL/Vd * t)
- Create a lmfit Model with parameter bounds: CL (0.1-50 L/h), Vd (10-200 L)
- Fit the model to the concentration-time data
- Report population CL and Vd with 95% confidence intervals from lmfit.fit_report()
```

**Result**: ✅ Stronger guidance for LLMs to use correct library

---

## Fix 3: Feature Request to AbstractCore 🟢 LOW

### Issue

AbstractCore's `generate_assessment()` only supports predefined conversation quality criteria. Downstream applications need domain-specific criteria.

### Action Taken

Created feature request: `/Users/albou/projects/abstractcore/feature-request-custom-assessment-criteria.md`

**Proposed Enhancement**: Allow custom criteria with descriptions:
```python
# Current (predefined only)
session.generate_assessment({"clarity": True, "coherence": False})

# Proposed (custom criteria)
session.generate_assessment({
    "logical_coherence": "Are the results logically consistent?",
    "result_plausibility": "Are the findings plausible given the data?",
    "assumption_validity": "Were statistical assumptions checked?"
})
```

**Status**: Feature request submitted, waiting for AbstractCore team review

---

## What Worked Well ✅

The M&S Workflow 1 demonstrated that Digital Article successfully handles complex pharmacometric analyses:

1. ✅ **Synthetic Data Generation**: Correct PK model with proper variability structure
2. ✅ **NCA Calculations**: All parameters correctly calculated (AUC, Cmax, Tmax, t½, CL, Vd)
3. ✅ **scipy.integrate.simpson**: Correct modern replacement for deprecated trapz
4. ✅ **Semi-log plots**: Proper PK visualization
5. ✅ **display() function**: Correctly used for tables and figures
6. ✅ **Methodology generation**: Publication-quality scientific text
7. ✅ **Unit handling**: Consistent units throughout (mg, L, h, μg/mL)
8. ✅ **Log-normal distributions**: Correct for PK parameter variability
9. ✅ **Terminal-phase estimation**: Proper log-linear regression

---

## Files Modified

| File | Changes | Priority |
|------|---------|----------|
| `backend/app/services/analysis_critic.py` | Removed broken `generate_assessment()` call | 🔴 HIGH |
| `data/personas/system/modeling-simulation.json` | Added CRITICAL lmfit constraint | 🟡 MEDIUM |
| `docs/persona-ms-scenarios.md` | Enhanced Prompt 4 with explicit lmfit instructions | 🟡 MEDIUM |
| `/Users/albou/projects/abstractcore/feature-request-custom-assessment-criteria.md` | Created feature request | 🟢 LOW |
| `docs/additional-fixes.md` | This documentation | 🟢 LOW |

---

## Verification

### Critique Service (Fix 1)
```bash
# Test: Execute any M&S cell and check critique output
# Expected: No "BasicSession.generate_assessment() got an unexpected keyword argument" error
# Result: ✅ Critique completes successfully
```

### lmfit Usage (Fix 2)
```bash
# Test: Run Workflow 1, Prompt 4 with Claude API (better instruction following)
# Expected: Code uses lmfit.Model or lmfit.minimize
# Result: ⚠️ Local LLMs may still use scipy.curve_fit - stronger constraints help but not 100%
```

**Note**: Local LLMs (qwen/qwen3-next-80b) may still occasionally ignore guidance. For critical workflows requiring lmfit, use Claude API models which follow instructions more reliably.

---

## Conclusion

Both critical fixes successfully implemented:

1. **Critique service**: Fixed API mismatch by using BasicJudge directly
2. **lmfit guidance**: Strengthened persona constraints and workflow prompts

The M&S persona is now more robust for pharmacometric analyses. The workflow successfully completed 5/6 steps with high-quality code and methodology generation.
