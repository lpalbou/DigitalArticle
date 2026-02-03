# Logic Self-Correction Loop

> **ADR**: [0004-recursive-self-correction-loop.md](../adr/0004-recursive-self-correction-loop.md)  
> **Backlog**: [0009_logic_self_correction_loop.md](../backlog/completed/0009_logic_self_correction_loop.md)

## Toggle (User Settings)

Logic validation can be enabled/disabled in Settings:

```json
{
  "execution": {
    "logic_validation_enabled": true,
    "max_logic_corrections": 2,
    "medium_retry_max_corrections": 0,
    "low_retry_max_corrections": 0
  }
}
```

When **enabled**, you'll always see 3+ LLM calls per cell:
1. **Code Generation**
2. **Logic Validation** ← NEW (even when passing)
3. **Methodology Generation**

---

## The Problem

Code that **executes successfully** can still be **semantically wrong**:

| What the user asked | What the LLM generated | What's wrong |
|---------------------|------------------------|--------------|
| "Compare groups A and B" | `stats.ttest_ind(a, b)` | Data isn't normally distributed → should use Mann-Whitney U |
| "Show a scatter plot" | `df.describe()` | No plot generated, just statistics |
| "Calculate the p-value" | `print(result)` | P-value not visible in output (print vs display) |
| "Analyze survival data" | Kaplan-Meier without log-rank test | Missing statistical comparison |

The execution retry loop only catches **runtime errors** (code doesn't run).  
The logic correction loop catches **semantic errors** (code runs but answer is wrong).

---

## Two Loops: Execution vs Logic

```
┌────────────────────────────────────────────────────────────────────┐
│                                                                    │
│   LOOP A: Execution Correctness (syntax/runtime)                  │
│                                                                    │
│   ┌──────────────┐    error    ┌──────────────┐                   │
│   │  Code Gen    │────────────▶│  Code Fix    │                   │
│   └──────────────┘             └──────────────┘                   │
│          │                            │                           │
│          │ success                    │ re-execute                │
│          ▼                            │                           │
│   ┌──────────────┐◀───────────────────┘                           │
│   │   Execute    │                                                │
│   └──────────────┘                                                │
│          │                                                        │
│          │ success                                                │
│          ▼                                                        │
└──────────┼────────────────────────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────────────────────────┐
│                                                                    │
│   LOOP B: Logic Correctness (semantic)                            │
│                                                                    │
│   ┌──────────────┐    fail     ┌──────────────┐                   │
│   │ Logic Valid. │────────────▶│ Logic Fix    │                   │
│   └──────────────┘             └──────────────┘                   │
│          │                            │                           │
│          │ pass                       │ back to LOOP A            │
│          ▼                            │ (fixed code might break)  │
│   ┌──────────────┐◀───────────────────┘                           │
│   │ Methodology  │                                                │
│   └──────────────┘                                                │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

**Key insight**: Loop B can trigger Loop A. If logic correction changes the code, we must re-execute (which might fail and trigger runtime fixes).

---

## Two-Stage Validation

```
┌─────────────────────────────────────────────────────────────┐
│ Stage 1: Heuristic Checks (fast, deterministic, free)       │
│                                                             │
│  • No plots when visualization requested?                   │
│  • No tables when data display requested?                   │
│  • Using print() instead of display()?                      │
│  • Statistical test without p-value in output?              │
│                                                             │
│  → If any FAIL: skip LLM, return issues immediately         │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼ (if heuristics pass)
┌─────────────────────────────────────────────────────────────┐
│ Stage 2: LLM-as-Judge (thorough, semantic, 1 LLM call)      │
│                                                             │
│  • Does the code actually do what the prompt asks?          │
│  • Are statistical assumptions validated?                   │
│  • Is the correct test used for the data type?              │
│  • Are results properly displayed and interpreted?          │
│                                                             │
│  → Returns: PASS | FAIL (with issues + suggestions)         │
└─────────────────────────────────────────────────────────────┘
```

---

## Heuristic Checks (Stage 1)

These are **free** (no LLM call) and **deterministic**:

### 1. Missing Visualization

**Trigger**: Prompt contains `plot`, `chart`, `graph`, `figure`, `visualize`, `show`  
**Check**: `result.plots` is empty  
**Issue**: "Prompt requests visualization but no plot was generated"  
**Suggestion**: "Add code to create and display a plot using matplotlib/seaborn/plotly"

### 2. Missing Table Display

**Trigger**: Prompt contains `table`, `dataframe`, `show data`, `display`  
**Check**: `result.tables` is empty AND no stdout  
**Issue**: "Prompt requests data display but no table was generated"  
**Suggestion**: "Add display(df, 'Table: Description') to show the data"

### 3. Using print() Instead of display()

**Trigger**: Code contains `print(` but not `display(`  
**Check**: Has stdout but no plots/tables  
**Issue**: "Code uses print() instead of display() for results"  
**Suggestion**: "Replace print() with display(result, 'Label') for proper rendering"

### 4. Statistical Test Without Key Metrics

**Trigger**: Prompt contains `t-test`, `anova`, `chi-square`, `correlation`, `regression`, `p-value`, `hypothesis`  
**Check**: Output doesn't contain `p`, `statistic`, or `coefficient`  
**Issue**: "Statistical analysis requested but p-value/test statistic not visible in output"  
**Suggestion**: "Display the test statistic, p-value, and effect size"

---

## LLM Validation (Stage 2)

If heuristics pass, the LLM is asked to validate semantic correctness.

### Validation Prompt Structure

```
VALIDATE THIS ANALYSIS:

USER PROMPT:
{original user prompt}

GENERATED CODE:
```python
{executed code}
```

EXECUTION OUTPUT:
{stdout from execution}

OUTPUT SUMMARY:
STATIC_PLOTS GENERATED: {count}
INTERACTIVE_PLOTS GENERATED: {count}  # Plotly
IMAGES GENERATED: {count}
TABLES GENERATED: {count}

Does this code correctly answer the user's prompt? Check for methodological issues.
```

### What the LLM Checks

1. **Intent alignment**: Does the code do what the user asked?
2. **Correct methodology**: Right statistical test for the data type?
3. **Assumption validation**: Normality checks before t-test?
4. **Proper output**: Results displayed, not just calculated?
5. **Domain best practices**: Using persona guidance if available

### LLM Response Format

```
RESULT: PASS or FAIL
ISSUES:
- [HIGH] Issue 1 | evidence_code: `<substring from code>` | evidence_output: `<substring from output>`
- [MEDIUM] Issue 2 | evidence_code: `NONE` | evidence_output: `<substring from output>`
SUGGESTIONS:
- Suggestion 1
- Suggestion 2
CONFIDENCE: 0.85
```

#### Evidence requirement (anti-hallucination)

To reduce “LLM judge hallucinated an issue” failures, each issue must include **verifiable evidence**:
- `evidence_code`: a verbatim snippet copied from the provided code (or `NONE`)
- `evidence_output`: a verbatim snippet copied from the execution output (or `NONE`)

If evidence is missing or can’t be verified, the system **downgrades severity** and will not trigger aggressive correction.

#### Compaction markers (ADR 0003)

To control LLM context size without silently hiding information, long code/stdout may be compacted with explicit markers inside the validator prompt:

```
#COMPACTION_NOTICE: CODE compacted for LLM context (original_len=..., shown=head+tail=...; middle omitted).
```

This is logged at **INFO** and is visible in the stored trace prompt.

---

## Issue Severity Levels

Issues are categorized by severity to prioritize what gets fixed:

| Severity | Action | Examples |
|----------|--------|----------|
| **HIGH** | MUST fix - triggers correction loop | Wrong test, incorrect logic, missing critical step |
| **MEDIUM** | SHOULD fix - logged but doesn't trigger correction | Missing assumptions, suboptimal method |
| **LOW** | NICE to have - ignored | Style issues, minor improvements |

**Correction triggering is policy-driven (user-configurable):**
- **HIGH**: always eligible to trigger correction (bounded by `execution.max_logic_corrections`)
- **MEDIUM/LOW**: can be enabled with thresholds (`execution.medium_retry_max_corrections`, `execution.low_retry_max_corrections`)

**Default policy**: only HIGH issues are auto-corrected (MEDIUM/LOW are logged for the user).

This prevents over-correction and wasted LLM calls on minor issues while still allowing users to opt into stricter behavior.

---

## Correction Loop

When validation FAILS, the system attempts to fix the code **if the configured policy allows it** (based on the highest severity present and current correction count):

```
┌──────────────────────────────────────────────────────────────┐
│ 1. Validation FAIL detected                                  │
│    Issues: ["Using t-test on non-normal data"]               │
│    Suggestions: ["Use Mann-Whitney U test instead"]          │
└──────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│ 2. Ask LLM to fix (asuggest_improvements)                    │
│                                                              │
│    "The code executed successfully but has these issues:     │
│     - Using t-test on non-normal data                        │
│                                                              │
│    Suggestions to fix:                                       │
│     - Use Mann-Whitney U test instead                        │
│                                                              │
│    Please fix the code to correctly answer the original      │
│    prompt."                                                  │
└──────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│ 3. Execute fixed code                                        │
└──────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│ 4. Re-validate (back to Stage 1)                             │
│    → If PASS: done                                           │
│    → If FAIL: retry (up to 2 times)                          │
└──────────────────────────────────────────────────────────────┘
```

### Bounded Loop

**Maximum attempts**: 2 (configurable in `NotebookService`)

**Stop conditions**:
- PASS: Validation succeeds
- UNCERTAIN: Validator cannot determine (edge case)
- Exhausted: 2 attempts failed
- Fixed code fails execution: Revert to original

---

## Transparency & Observability

All validation results are stored in `cell.metadata.logic_validation`:

```json
{
  "logic_validation": [
    {
      "attempt": 1,
      "result": "fail",
      "issues": ["Using t-test on non-normal data"],
      "suggestions": ["Use Mann-Whitney U test instead"],
      "confidence": 0.85,
      "validation_type": "llm"
    },
    {
      "attempt": 2,
      "result": "pass",
      "issues": [],
      "suggestions": [],
      "confidence": 0.92,
      "validation_type": "llm"
    }
  ]
}
```

If issues remain unresolved after exhausting attempts:

```json
{
  "execution": {
    "logic_correction_count": 2,
    "logic_issues_unresolved": ["Some remaining issue"]
  }
}
```

---

## Persona Integration

If the notebook has active personas, their REVIEW guidance is injected into the LLM validation prompt:

```python
# In LogicValidationService._build_validation_system_prompt():
if persona_combination:
    guidance = persona_combination.effective_guidance.get(PersonaScope.REVIEW)
    if guidance:
        prompt += f"\nDOMAIN-SPECIFIC VALIDATION RULES:\n{guidance.system_prompt_addition}"
```

This means a **Statistician** persona can add rules like:
- "Always check normality before parametric tests"
- "Report effect sizes, not just p-values"
- "Use Bonferroni correction for multiple comparisons"

---

## Cost Considerations

| Stage | Cost | When triggered |
|-------|------|----------------|
| Heuristic checks | Free | Always (after successful execution) |
| LLM validation | ~500-1000 tokens | Only if heuristics pass |
| LLM fix | ~1000-2000 tokens | Only if validation FAIL |

**Total worst case** (2 corrections): ~5000 tokens extra per cell  
**Typical case** (pass on first try): ~500 tokens extra per cell

---

## Files

| File | Purpose |
|------|---------|
| `backend/app/services/logic_validation_service.py` | Core validation logic |
| `backend/app/services/notebook_service.py` | Integration in execute_cell() |
| `tests/logic_validation/test_logic_validation_service.py` | Tests |
| `docs/adr/0004-recursive-self-correction-loop.md` | Architecture decision |
