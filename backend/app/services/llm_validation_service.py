"""
LLM-Based Validation Service for Digital Article

This service uses LLM reasoning to evaluate validation rules against code execution,
providing semantic validation instead of simple pattern matching.

The LLM receives:
- Code that was executed
- Execution results (stdout, tables)
- Available variables from previous cells
- Validation rules (ensure/prevent checks)

And returns structured validation results with reasoning and evidence.
"""

import logging
import json
import re
from typing import Dict, Any, List, Tuple, Optional

from ..models.validation import (
    ValidationResult,
    ValidationReport,
    ValidationPhase,
    ValidationSeverity
)

logger = logging.getLogger(__name__)


class LLMValidationService:
    """LLM-based semantic validation service."""

    VALIDATION_SYSTEM_PROMPT = """You are a scientific code validator for data analysis.

## YOUR TASK
Evaluate code execution against TWO types of validation rules:

1. **ENSURE checks**: Verify something IS present/valid/happening
   - PASS if the condition is satisfied
   - FAIL if the condition is NOT satisfied

2. **PREVENT checks**: Verify something is NOT present/happening
   - PASS if the anti-pattern is ABSENT
   - FAIL if the anti-pattern is DETECTED

For each rule, provide:
- Whether it PASSED or FAILED
- Specific evidence from the code/output
- Clear reasoning

## CRITICAL REQUIREMENTS
- Be SPECIFIC: Reference actual values, line numbers, variable names
- Be HONEST: Only flag REAL issues you can prove from the evidence
- Be HELPFUL: Provide actionable suggestions for failures
- Be THOROUGH: Check ALL rules, don't skip any

## OUTPUT FORMAT (JSON)
Return a JSON object with two arrays: "ensure_results" and "prevent_results"

```json
{
  "ensure_results": [
    {
      "name": "uses_existing_variables",
      "passed": true,
      "reasoning": "Code correctly uses existing 'patient_df' from previous cell"
    },
    {
      "name": "correct_column_references",
      "passed": false,
      "severity": "error",
      "reasoning": "References column 'AGE_YEARS' but DataFrame only has 'AGE'",
      "evidence": "Line 12: df['AGE_YEARS'] but patient_df.columns shows ['AGE', 'SEX', 'ARM']",
      "suggestion": "Use 'AGE' instead of 'AGE_YEARS'"
    }
  ],
  "prevent_results": [
    {
      "name": "circular_reasoning",
      "passed": true,
      "reasoning": "Code predicts 'RESPONSE' outcome, not group assignment"
    },
    {
      "name": "data_leakage",
      "passed": false,
      "severity": "error",
      "reasoning": "Model fitted on test data before train data",
      "evidence": "Line 25: model.fit(X_test, y_test) appears before model.fit(X_train, y_train)",
      "suggestion": "Only fit on training data, then predict on test data"
    }
  ]
}
```"""

    def __init__(self, llm_service):
        """
        Initialize LLM validation service.

        Args:
            llm_service: LLMService instance for calling the LLM
        """
        self.llm_service = llm_service

    def validate(
        self,
        code: str,
        execution_result: Dict[str, Any],
        context: Dict[str, Any],
        ensure_rules: List[Dict],
        prevent_rules: List[Dict]
    ) -> Tuple[List[ValidationResult], Optional[str], Optional[Dict]]:
        """
        Run LLM-based validation.

        Args:
            code: Python code that was executed
            execution_result: Execution output (stdout, tables, etc.)
            context: Execution context (available variables, previous cells)
            ensure_rules: List of ENSURE check rules
            prevent_rules: List of PREVENT check rules

        Returns:
            Tuple of (validation_results, trace_id, full_trace)
        """
        if not ensure_rules and not prevent_rules:
            logger.info("No validation rules to check")
            return [], None, None

        try:
            # Build LLM prompts
            user_prompt = self._build_user_prompt(
                code, execution_result, context, ensure_rules, prevent_rules
            )

            # Call LLM for validation
            response = self.llm_service.llm.generate(
                user_prompt,
                system_prompt=self.VALIDATION_SYSTEM_PROMPT,
                trace_metadata={
                    'step_type': 'llm_validation',
                    'notebook_id': context.get('notebook_id'),
                    'cell_id': context.get('cell_id'),
                },
                temperature=0.1,  # Low temp for consistent validation
                max_tokens=32000,
                max_output_tokens=8192
            )

            # Extract trace for observability
            trace_id = response.metadata.get('trace_id') if hasattr(response, 'metadata') else None
            full_trace = self.llm_service.llm.get_traces(trace_id=trace_id) if trace_id else None

            # Parse structured response
            results = self._parse_response(response.content, ensure_rules, prevent_rules)

            logger.info(f"✅ LLM validation complete: {len(results)} findings")

            return results, trace_id, full_trace

        except Exception as e:
            logger.error(f"LLM validation failed: {e}")
            logger.error(f"Traceback:", exc_info=True)
            return [], None, None

    def _build_user_prompt(
        self,
        code: str,
        execution_result: Dict[str, Any],
        context: Dict[str, Any],
        ensure_rules: List[Dict],
        prevent_rules: List[Dict]
    ) -> str:
        """Build comprehensive user prompt with code + context + rules."""

        prompt = f"""## CODE TO VALIDATE
```python
{code}
```

## EXECUTION OUTPUT
```
{execution_result.get('stdout', '')[:5000]}
```

## TABLES GENERATED
{self._format_tables(execution_result.get('tables', []))}

## AVAILABLE VARIABLES (from previous cells)
{self._format_context(context)}

---

## ENSURE CHECKS (must be satisfied)
"""
        for rule in ensure_rules:
            prompt += f"""
### {rule['name']}
{rule['check']}
**Severity**: {rule.get('severity', 'warning')}
"""

        prompt += """

## PREVENT CHECKS (must NOT occur)
"""
        for rule in prevent_rules:
            prompt += f"""
### {rule['name']}
{rule['check']}
**Severity**: {rule.get('severity', 'warning')}
"""

        prompt += """
---

Evaluate ALL rules above. Return results as JSON with 'ensure_results' and 'prevent_results' arrays."""

        return prompt

    def _format_tables(self, tables: List[Dict]) -> str:
        """Format tables for LLM context."""
        if not tables:
            return "No tables generated"

        formatted = []
        for table in tables[:5]:  # Limit to first 5 tables
            name = table.get('name', 'Unknown')
            shape = table.get('shape', [0, 0])
            columns = table.get('columns', [])
            formatted.append(f"- **{name}**: {shape[0]} rows × {shape[1]} cols, columns: {columns[:10]}")

        return "\n".join(formatted)

    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context for LLM."""
        if not context or 'available_variables' not in context:
            return "No variables from previous cells"

        variables = context['available_variables']
        formatted = []

        for var_name, var_info in list(variables.items())[:10]:  # Limit to 10 vars
            if isinstance(var_info, str):
                formatted.append(f"- {var_name}: {var_info}")
            elif isinstance(var_info, dict):
                var_type = var_info.get('type', 'Unknown')
                if 'DataFrame' in var_type and 'shape' in var_info:
                    shape = var_info.get('shape', [0, 0])
                    columns = var_info.get('columns', [])
                    formatted.append(f"- {var_name}: DataFrame ({shape[0]} rows × {shape[1]} cols, columns: {columns[:5]}...)")
                else:
                    formatted.append(f"- {var_name}: {var_type}")

        return "\n".join(formatted) if formatted else "No variables available"

    def _parse_response(
        self,
        response_content: str,
        ensure_rules: List[Dict],
        prevent_rules: List[Dict]
    ) -> List[ValidationResult]:
        """Parse LLM validation response into ValidationResults."""

        results = []

        try:
            # Extract JSON from response (may be in code block)
            json_match = re.search(r'```json\s*(.*?)\s*```', response_content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
            else:
                # Try to parse entire response as JSON
                data = json.loads(response_content)

            # Process ensure_results
            for validation in data.get('ensure_results', []):
                rule_name = validation.get('name', 'unknown')
                passed = validation.get('passed', True)

                if not passed:
                    # Find rule config for severity
                    rule_config = next(
                        (r for r in ensure_rules if r['name'] == rule_name),
                        {}
                    )

                    results.append(ValidationResult(
                        validator_name=f"ensure.{rule_name}",
                        phase=ValidationPhase.LOGICAL,
                        passed=False,
                        severity=ValidationSeverity(validation.get('severity', rule_config.get('severity', 'warning'))),
                        message=validation.get('reasoning', 'Validation failed'),
                        details=validation.get('evidence'),
                        suggestion=validation.get('suggestion', rule_config.get('suggestion'))
                    ))

            # Process prevent_results
            for validation in data.get('prevent_results', []):
                rule_name = validation.get('name', 'unknown')
                passed = validation.get('passed', True)

                if not passed:
                    # Find rule config for severity
                    rule_config = next(
                        (r for r in prevent_rules if r['name'] == rule_name),
                        {}
                    )

                    results.append(ValidationResult(
                        validator_name=f"prevent.{rule_name}",
                        phase=ValidationPhase.LOGICAL,
                        passed=False,
                        severity=ValidationSeverity(validation.get('severity', rule_config.get('severity', 'warning'))),
                        message=validation.get('reasoning', 'Validation failed'),
                        details=validation.get('evidence'),
                        suggestion=validation.get('suggestion', rule_config.get('suggestion'))
                    ))

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM validation response: {e}")
            logger.error(f"Response content: {response_content[:500]}")
            # Fallback: try to extract findings from text
            results.extend(self._fallback_parse(response_content, ensure_rules, prevent_rules))

        except Exception as e:
            logger.error(f"Error parsing validation response: {e}")

        return results

    def _fallback_parse(
        self,
        response_content: str,
        ensure_rules: List[Dict],
        prevent_rules: List[Dict]
    ) -> List[ValidationResult]:
        """Fallback parser for non-JSON responses."""
        results = []

        # Try to extract failures mentioned in text
        for rule in ensure_rules:
            if f"failed" in response_content.lower() and rule['name'] in response_content.lower():
                results.append(ValidationResult(
                    validator_name=f"ensure.{rule['name']}",
                    phase=ValidationPhase.LOGICAL,
                    passed=False,
                    severity=ValidationSeverity(rule.get('severity', 'warning')),
                    message=f"LLM indicated {rule['name']} may have failed (fallback parsing)",
                    suggestion=rule.get('suggestion')
                ))

        for rule in prevent_rules:
            if f"failed" in response_content.lower() and rule['name'] in response_content.lower():
                results.append(ValidationResult(
                    validator_name=f"prevent.{rule['name']}",
                    phase=ValidationPhase.LOGICAL,
                    passed=False,
                    severity=ValidationSeverity(rule.get('severity', 'warning')),
                    message=f"LLM indicated {rule['name']} may have failed (fallback parsing)",
                    suggestion=rule.get('suggestion')
                ))

        return results
