# Custom Validators for Digital Article

Digital Article uses a **two-path validation system** to ensure code quality:

1. **Execution Validation** (Path 1): Fixes code that fails to run (syntax errors, imports, types)
2. **Logical Validation** (Path 2): Fixes code that runs but produces invalid/meaningless results

This document explains how to add custom validation rules for domain-specific requirements.

---

## Overview

Logical validators run **AFTER** code executes successfully to catch methodological issues, statistical problems, and domain violations. The system:

- ✅ Runs automatically after each cell execution
- ✅ Validates methodology, statistics, and data integrity
- ✅ Triggers automatic retry (up to 3 attempts) when errors found
- ✅ Provides clear guidance to the LLM for fixing issues
- ✅ Supports user-defined rules via simple YAML files

---

## Quick Start

### 1. View Built-in Validators

Open `data/validators/default.yaml` to see the built-in validators that ship with Digital Article:

```bash
cat data/validators/default.yaml
```

This file includes validators for:
- Statistical validity (%CV, parameters at bounds, impossible CIs)
- Logical coherence (circular reasoning, data leakage)
- Data integrity (missing columns, empty DataFrames)
- Best practices (p-values, sample sizes, multiple testing)

### 2. Create Your Own Validator

Create a new file in `data/validators/` (e.g., `my_domain.yaml`):

```yaml
version: "1.0"

validators:
  my_custom_validator:
    enabled: true
    severity: error  # error = triggers retry, warning = passive
    description: "Checks specific to my domain"

    rules:
      - name: "my_rule"
        description: "What this rule checks"
        check_stdout_for:
          - "pattern to find"
        message: "Error message shown to user"
        suggestion: "How to fix the issue"
```

### 3. Restart Backend

```bash
# Validators are loaded at startup
da-backend
```

Your custom validators will be automatically loaded and run after every cell execution.

---

## Validator Structure

### Basic Template

```yaml
version: "1.0"

validators:
  validator_name:
    enabled: true           # true/false to enable/disable
    severity: error         # error, warning, or info
    description: "Purpose"  # What this validator checks

    rules:
      - name: "rule_name"
        description: "What this rule checks"
        # ... checks (see below)
        message: "Error message"
        suggestion: "Fix recommendation"
```

### Severity Levels

| Level | Behavior |
|-------|----------|
| `error` | **Blocks execution** - Triggers automatic retry (up to 3 attempts) |
| `warning` | **Passive** - Shown to user but no retry |
| `info` | **Informational** - Just for logging |

---

## Check Types

### 1. Check Console Output for Patterns

Find specific strings in stdout:

```yaml
rules:
  - name: "parameter_at_bounds"
    check_stdout_for:
      - "at lower bound"
      - "at upper bound"
      - "hit bound"
    message: "Parameter(s) at optimizer bounds"
    suggestion: "Try different initial values"
```

### 2. Check Console Output with Regex

Match patterns using regular expressions:

```yaml
rules:
  - name: "impossible_confidence_interval"
    check_stdout_regex: "95%\\s*CI.*\\[?(-\\d+\\.?\\d*)"
    message: "CI includes negative values for positive parameter"
    suggestion: "Review model specification"
```

### 3. Check Code for Patterns

Find suspicious patterns in generated code:

```yaml
rules:
  - name: "data_leakage"
    check_code_for:
      - "fit.*X_test"
      - "fit.*y_test"
      - "transform.*test.*fit"
    message: "Test data used during training"
    suggestion: "Keep test data separate"
```

### 4. Check for Circular Reasoning

Detect prediction of grouping variables:

```yaml
rules:
  - name: "circular_reasoning"
    check_code_for_target_variable:
      suspicious_names: ["arm", "treatment", "group", "cohort"]
    message: "Predicting grouping variable"
    suggestion: "Predict an outcome, not group assignment"
```

### 5. Validate Table Values

Check tables for threshold violations:

```yaml
rules:
  - name: "coefficient_of_variation"
    check_tables_for:
      column_contains: ["%CV", "CV%"]
      threshold_above: 100
    message: "Poor parameter precision (%CV > 100%)"
    suggestion: "Model overparameterized or insufficient data"
```

**Table check options:**
- `column_contains`: List of column name patterns to find
- `threshold_above`: Flag if values > threshold
- `threshold_below`: Flag if values < threshold
- `shape_rows_below`: Flag if row count < threshold

### 6. Check Column References

Validate code uses existing DataFrame columns:

```yaml
rules:
  - name: "missing_columns"
    check_code_column_references: true
    compare_to_available_columns: true
    message: "Code references non-existent columns"
    suggestion: "Use df.columns.tolist() to see available columns"
```

---

## Domain-Specific Examples

### Clinical Trials Validator

```yaml
# File: data/validators/clinical_trials.yaml
version: "1.0"

validators:
  clinical_compliance:
    enabled: true
    severity: error
    description: "Clinical trial regulatory compliance"

    rules:
      - name: "intent_to_treat"
        description: "Use ITT population by default"
        check_code_for:
          - "per.protocol"
          - "completers.only"
        message: "Using per-protocol instead of ITT"
        suggestion: "Use intent-to-treat unless justified"

      - name: "missing_adverse_events"
        check_stdout_regex: "efficacy|effectiveness"
        message: "Efficacy reported but no adverse events"
        suggestion: "Include AE analysis for safety profile"

      - name: "sample_size_check"
        check_stdout_regex: "n\\s*=\\s*([0-9]+)"
        message: "Check sample size adequacy"
        suggestion: "Verify sample size meets protocol requirements"
```

### Pharmacokinetics Validator

```yaml
# File: data/validators/pharmacokinetics.yaml
version: "1.0"

validators:
  pk_analysis:
    enabled: true
    severity: error
    description: "PK/PD analysis checks"

    rules:
      - name: "negative_clearance"
        check_tables_for:
          column_contains: ["CL", "clearance"]
          threshold_below: 0
        message: "Negative clearance estimate"
        suggestion: "Model misspecification or data error"

      - name: "unrealistic_half_life"
        check_stdout_regex: "t1/2.*>.*1000"
        message: "Half-life > 1000 hours unrealistic"
        suggestion: "Check units or model structure"

      - name: "missing_dose_normalization"
        check_code_for:
          - "dose.*level"
          - "multiple.*dose"
        message: "Multiple doses without normalization"
        suggestion: "Normalize by dose for comparison"
```

### Machine Learning Validator

```yaml
# File: data/validators/machine_learning.yaml
version: "1.0"

validators:
  ml_best_practices:
    enabled: true
    severity: warning  # Warning only, no retry
    description: "ML best practices"

    rules:
      - name: "no_train_test_split"
        check_code_for:
          - "fit.*predict"
        message: "No train/test split detected"
        suggestion: "Use train_test_split for validation"

      - name: "no_cross_validation"
        check_code_for:
          - "GridSearchCV"
          - "RandomizedSearchCV"
        message: "Hyperparameter tuning without CV"
        suggestion: "Use cross-validation to prevent overfitting"

      - name: "class_imbalance"
        check_stdout_regex: "accuracy.*>.*0\\.95"
        message: "Very high accuracy may indicate class imbalance"
        suggestion: "Check class distribution and use balanced metrics"
```

---

## Advanced Usage

### Combining Multiple Checks

A single rule can have multiple check types:

```yaml
rules:
  - name: "comprehensive_check"
    # Check code
    check_code_for:
      - "problematic_pattern"
    # Check output
    check_stdout_for:
      - "error indicator"
    # Check tables
    check_tables_for:
      column_contains: ["metric"]
      threshold_above: 100
    message: "Multiple issues detected"
    suggestion: "Review methodology"
```

### Per-Rule Severity

Override default severity for specific rules:

```yaml
validators:
  my_validator:
    enabled: true
    severity: warning  # Default

    rules:
      - name: "minor_issue"
        # Uses default severity: warning
        message: "Minor issue"

      - name: "critical_issue"
        severity: error  # Override: triggers retry
        message: "Critical issue"
```

### Conditional Logic

Use regex captures for context-aware messages:

```yaml
rules:
  - name: "sample_size_warning"
    check_stdout_regex: "n\\s*=\\s*([0-9]+)"
    message: "Sample size {n} detected - verify adequacy"
    suggestion: "Consider power analysis for {n} samples"
```

---

## Best Practices

### 1. Start Simple

Begin with a few critical rules and expand gradually:

```yaml
# Start with one essential check
rules:
  - name: "critical_check"
    check_stdout_for: ["fatal error"]
    message: "Critical issue"
    severity: error

# Add more rules as needed
```

### 2. Use Descriptive Names

Make rule names self-explanatory:

```yaml
# Good
- name: "negative_clearance_estimate"

# Bad
- name: "check1"
```

### 3. Provide Clear Messages

Error messages should explain **what** failed and **why** it matters:

```yaml
# Good
message: "Parameter CL=0.5 at lower bound (0.5) - unreliable estimate"
suggestion: "Try initial value CL=5.0 or check data quality"

# Bad
message: "Error"
suggestion: "Fix it"
```

### 4. Group Related Rules

Organize rules by domain or concern:

```yaml
validators:
  data_quality:
    rules:
      - name: "missing_values"
      - name: "outliers"
      - name: "duplicates"

  statistical_validity:
    rules:
      - name: "assumptions"
      - name: "power"
      - name: "multiplicity"
```

### 5. Test Incrementally

Add one rule at a time and test:

```bash
# 1. Add one rule to YAML file
# 2. Restart backend
# 3. Test with notebook that should trigger it
# 4. Verify error message and LLM fix
# 5. Add next rule
```

---

## Troubleshooting

### Validator Not Running

**Problem**: Rule doesn't seem to execute

**Solutions**:
1. Check YAML syntax: `python -m yaml data/validators/my_file.yaml`
2. Verify `enabled: true` is set
3. Restart backend to reload validators
4. Check backend logs for loading errors

### Pattern Not Matching

**Problem**: Check should trigger but doesn't

**Solutions**:
1. Test pattern separately: Use Python regex tester
2. Check stdout format: Print actual output to see format
3. Use broader patterns: Start general, then refine
4. Check case sensitivity: Patterns are case-insensitive by default

### Too Many False Positives

**Problem**: Rule triggers incorrectly

**Solutions**:
1. Make patterns more specific
2. Add exclusion conditions
3. Change severity to `warning` instead of `error`
4. Use `check_code_for_target_variable` for smarter detection

### LLM Not Fixing Issues

**Problem**: Retry happens but LLM doesn't fix

**Solutions**:
1. Improve `suggestion` field with concrete examples
2. Add context in `message` field
3. Check if fix is actually possible with available data
4. Review LLM traces to see what guidance it received

---

## Reference

### Complete Example

See `data/validators/default.yaml` for a comprehensive example with:
- Statistical validity checks
- Logical coherence detection
- Data integrity verification
- Best practices recommendations

### Validator Statistics

View loaded validators:

```python
# In Python shell
from backend.app.services.validation_service import ValidationService

service = ValidationService()
stats = service.get_validator_stats()
print(stats)
```

### Reload Validators

During development, reload without restart:

```python
# In notebook cell
service.reload_yaml_validators()
```

---

## Support

For questions or issues:

1. **Check default validators**: `data/validators/default.yaml` has many examples
2. **Review error logs**: Backend logs show validation execution and failures
3. **Test with simple cases**: Create minimal notebooks to isolate issues
4. **File GitHub issue**: Report bugs or request features

---

## Next Steps

1. **Review built-in validators**: Open `data/validators/default.yaml`
2. **Identify domain needs**: What methodological errors occur in your domain?
3. **Create custom validator**: Start with one critical check
4. **Test thoroughly**: Verify detection and LLM fixing
5. **Expand gradually**: Add more rules as you identify patterns

Happy validating! 🧪
