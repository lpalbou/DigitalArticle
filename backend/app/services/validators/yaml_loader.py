"""
YAML Validator Loader for Digital Article

Loads and executes YAML-defined validation rules from data/validators/ directory.
This provides a user-friendly way to define custom validators without writing Python code.

YAML validators can check:
- stdout/stderr for specific patterns
- Code for suspicious patterns
- Tables for threshold violations
- DataFrames for column mismatches

See data/validators/default.yaml for examples and documentation.
"""

import yaml
import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from ...models.validation import (
    ValidationResult,
    ValidationPhase,
    ValidationSeverity
)
from ...config import config

logger = logging.getLogger(__name__)


class YAMLValidatorLoader:
    """
    Loads and executes YAML-defined validation rules.

    This class scans data/validators/ for .yaml files, parses their validation
    rules, and provides a validate() method that runs all enabled rules against
    code and execution results.
    """

    def __init__(self, validators_dir: Optional[str] = None):
        """
        Initialize the YAML validator loader.

        Args:
            validators_dir: Directory containing .yaml validator files (defaults to config.get_validators_dir())
        """
        # Use config if no explicit path provided
        if validators_dir is None:
            validators_dir = config.get_validators_dir()
        self.validators_dir = Path(validators_dir)
        self.rules = {}  # Old schema (v1.0) - pattern-based
        self.ensure_rules = []  # New schema (v2.0) - LLM-based
        self.prevent_rules = []  # New schema (v2.0) - LLM-based
        self.schema_version = "1.0"  # Default to old schema
        self._load_all_rules()

    def _load_all_rules(self) -> None:
        """
        Load all YAML files from validators directory.

        Scans the validators directory for .yaml files and loads their
        validation rules into self.rules dict.
        """
        if not self.validators_dir.exists():
            logger.warning(f"Validators directory does not exist: {self.validators_dir}")
            logger.warning("No YAML validators will be loaded. Create data/validators/ and add .yaml files.")
            return

        yaml_files = list(self.validators_dir.glob("*.yaml"))
        if not yaml_files:
            logger.warning(f"No .yaml files found in {self.validators_dir}")
            return

        logger.info(f"Loading YAML validators from {self.validators_dir}")

        for yaml_file in yaml_files:
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)

                # Check schema version
                version = config.get('version', '1.0')

                if version == '2.0':
                    # New LLM-based schema with ensure/prevent
                    self.schema_version = '2.0'

                    if 'ensure' in config:
                        self.ensure_rules.extend(config['ensure'])
                        logger.info(f"Loaded {len(config['ensure'])} ENSURE rule(s) from {yaml_file.name}")

                    if 'prevent' in config:
                        self.prevent_rules.extend(config['prevent'])
                        logger.info(f"Loaded {len(config['prevent'])} PREVENT rule(s) from {yaml_file.name}")

                elif 'validators' in config:
                    # Old pattern-based schema (v1.0)
                    for validator_name, validator_config in config['validators'].items():
                        self.rules[validator_name] = validator_config
                    logger.info(f"Loaded {len(config['validators'])} validator(s) from {yaml_file.name}")
                else:
                    logger.warning(f"No 'validators', 'ensure', or 'prevent' key found in {yaml_file.name}")

            except yaml.YAMLError as e:
                logger.error(f"Failed to parse {yaml_file.name}: {e}")
            except Exception as e:
                logger.error(f"Error loading {yaml_file.name}: {e}")

        if self.schema_version == '2.0':
            logger.info(f"Loaded v2.0 schema: {len(self.ensure_rules)} ENSURE + {len(self.prevent_rules)} PREVENT rules")
        else:
            logger.info(f"Total YAML validators loaded: {len(self.rules)}")

    def validate(
        self,
        code: str,
        execution_result: Dict[str, Any],
        context: Dict[str, Any]
    ) -> List[ValidationResult]:
        """
        Run all YAML-defined validators and return results.

        Args:
            code: The Python code that was executed
            execution_result: Results from execution (stdout, stderr, tables, etc.)
            context: Additional context (available variables, etc.)

        Returns:
            List of ValidationResult objects (empty if all passed)
        """
        results = []

        for validator_name, validator_config in self.rules.items():
            # Skip if disabled
            if not validator_config.get('enabled', True):
                continue

            # Get default severity for this validator
            default_severity = validator_config.get('severity', 'warning')

            # Check all rules in this validator
            for rule in validator_config.get('rules', []):
                result = self._check_rule(
                    rule,
                    code,
                    execution_result,
                    context,
                    validator_name,
                    default_severity
                )
                if result:
                    results.append(result)

        return results

    def _check_rule(
        self,
        rule: Dict[str, Any],
        code: str,
        execution_result: Dict[str, Any],
        context: Dict[str, Any],
        validator_name: str,
        default_severity: str
    ) -> Optional[ValidationResult]:
        """
        Check a single rule against code/results.

        Args:
            rule: The rule configuration from YAML
            code: Python code
            execution_result: Execution results
            context: Additional context
            validator_name: Name of parent validator
            default_severity: Default severity from validator config

        Returns:
            ValidationResult if check failed, None if passed
        """
        passed = True
        message = None

        # CHECK 1: stdout patterns
        if 'check_stdout_for' in rule and passed:
            passed, message = self._check_stdout_patterns(
                rule['check_stdout_for'],
                execution_result.get('stdout', ''),
                rule
            )

        # CHECK 2: stdout regex
        if 'check_stdout_regex' in rule and passed:
            passed, message = self._check_stdout_regex(
                rule['check_stdout_regex'],
                execution_result.get('stdout', ''),
                rule
            )

        # CHECK 3: code patterns
        if 'check_code_for' in rule and passed:
            passed, message = self._check_code_patterns(
                rule['check_code_for'],
                code,
                rule
            )

        # CHECK 4: code target variable (for circular reasoning check)
        if 'check_code_for_target_variable' in rule and passed:
            passed, message = self._check_target_variable(
                rule['check_code_for_target_variable'],
                code,
                rule
            )

        # CHECK 5: table thresholds
        if 'check_tables_for' in rule and passed:
            passed, message = self._check_tables(
                rule['check_tables_for'],
                execution_result.get('tables', []),
                rule
            )

        # CHECK 6: code column references
        if 'check_code_column_references' in rule and passed:
            passed, message = self._check_column_references(
                rule,
                code,
                context,
                rule
            )

        # If check failed, create ValidationResult
        if not passed:
            severity_str = rule.get('severity', default_severity)
            severity = ValidationSeverity(severity_str)

            return ValidationResult(
                validator_name=f"{validator_name}.{rule['name']}",
                phase=ValidationPhase.LOGICAL,  # YAML validators are logical phase
                passed=False,
                severity=severity,
                message=message or rule.get('message', "Validation failed"),
                details=rule.get('description'),
                suggestion=rule.get('suggestion')
            )

        return None

    def _check_stdout_patterns(
        self,
        patterns: List[str],
        stdout: str,
        rule: Dict
    ) -> Tuple[bool, Optional[str]]:
        """Check if any patterns appear in stdout."""
        stdout_lower = stdout.lower()
        for pattern in patterns:
            if pattern.lower() in stdout_lower:
                return False, rule.get('message', f"Found '{pattern}' in output")
        return True, None

    def _check_stdout_regex(
        self,
        pattern: str,
        stdout: str,
        rule: Dict
    ) -> Tuple[bool, Optional[str]]:
        """Check if regex pattern matches stdout."""
        if re.search(pattern, stdout, re.IGNORECASE | re.MULTILINE):
            return False, rule.get('message', f"Pattern matched in output")
        return True, None

    def _check_code_patterns(
        self,
        patterns: List[str],
        code: str,
        rule: Dict
    ) -> Tuple[bool, Optional[str]]:
        """Check if any patterns appear in code."""
        for pattern in patterns:
            if re.search(pattern, code, re.IGNORECASE):
                return False, rule.get('message', f"Found suspicious pattern in code: {pattern}")
        return True, None

    def _check_target_variable(
        self,
        config: Dict[str, Any],
        code: str,
        rule: Dict
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if code predicts a grouping/assignment variable (circular reasoning).

        Looks for patterns like:
        - y = df['ARM']
        - target = df['TREATMENT']
        - predict(..., df['GROUP'])
        """
        suspicious_names = config.get('suspicious_names', [])
        if not suspicious_names:
            return True, None

        # Patterns to find target variable assignments
        target_patterns = [
            r"y\s*=\s*df\['([^']+)'\]",
            r"y\s*=\s*df\[\"([^\"]+)\"\]",
            r"target\s*=\s*df\['([^']+)'\]",
            r"target\s*=\s*df\[\"([^\"]+)\"\]",
            r"predict\(.*?df\['([^']+)'\]",
            r"predict\(.*?df\[\"([^\"]+)\"\]",
        ]

        for pattern in target_patterns:
            matches = re.findall(pattern, code, re.IGNORECASE)
            for column_name in matches:
                # Check if column name contains suspicious keywords
                column_lower = column_name.lower()
                for keyword in suspicious_names:
                    if keyword.lower() in column_lower:
                        return False, rule.get('message', f"Predicting '{column_name}' - likely a grouping variable")

        return True, None

    def _check_tables(
        self,
        config: Dict[str, Any],
        tables: List[Dict],
        rule: Dict
    ) -> Tuple[bool, Optional[str]]:
        """
        Check tables for threshold violations.

        Supports:
        - column_contains: Find columns with specific names
        - threshold_above: Flag if values exceed threshold
        - threshold_below: Flag if values below threshold
        - shape_rows_below: Flag if row count below threshold
        """
        column_patterns = config.get('column_contains', [])
        threshold_above = config.get('threshold_above')
        threshold_below = config.get('threshold_below')
        shape_rows_below = config.get('shape_rows_below')

        for table in tables:
            columns = table.get('columns', [])
            data = table.get('data', [])
            shape = table.get('shape', [0, 0])

            # Check shape
            if shape_rows_below is not None and shape[0] < shape_rows_below:
                return False, rule.get('message', f"Table has only {shape[0]} rows (expected >= {shape_rows_below})")

            # Check column values against thresholds
            if threshold_above is not None or threshold_below is not None:
                # Find columns matching patterns
                matching_cols = []
                for col in columns:
                    for pattern in column_patterns:
                        if pattern.lower() in str(col).lower():
                            matching_cols.append(col)
                            break

                # Check values in matching columns
                for row in data:
                    for col in matching_cols:
                        if col not in row:
                            continue

                        value = row[col]
                        if not isinstance(value, (int, float)):
                            continue

                        if threshold_above is not None and value > threshold_above:
                            return False, rule.get('message', f"{col}={value} exceeds threshold {threshold_above}")

                        if threshold_below is not None and value < threshold_below:
                            return False, rule.get('message', f"{col}={value} below threshold {threshold_below}")

        return True, None

    def _check_column_references(
        self,
        config: Dict[str, Any],
        code: str,
        context: Dict[str, Any],
        rule: Dict
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if code references columns that don't exist in available DataFrames.

        This helps catch data mismatch errors early.
        """
        if not config.get('compare_to_available_columns', False):
            return True, None

        available_vars = context.get('available_variables', {})

        # Extract column references from code
        # Pattern: df['column'] or df["column"]
        column_refs = re.findall(r"df\['([^']+)'\]|df\[\"([^\"]+)\"\]", code)
        referenced_columns = set(col for match in column_refs for col in match if col)

        # Get actual columns from available DataFrames
        actual_columns = set()
        for var_name, var_info in available_vars.items():
            if 'DataFrame' in str(var_info):
                # Extract columns if available in metadata
                if isinstance(var_info, dict) and 'columns' in var_info:
                    actual_columns.update(var_info['columns'])

        # Check for mismatches
        if referenced_columns and actual_columns:
            missing = referenced_columns - actual_columns
            if missing:
                return False, rule.get(
                    'message',
                    f"Code references columns that don't exist: {', '.join(list(missing)[:5])}"
                )

        return True, None


    def reload(self) -> None:
        """Reload all YAML validator files (useful during development)."""
        logger.info("Reloading YAML validators...")
        self.rules.clear()
        self.ensure_rules.clear()
        self.prevent_rules.clear()
        self._load_all_rules()

    def get_ensure_rules(self) -> List[Dict]:
        """
        Get ENSURE rules for LLM-based validation (v2.0 schema).

        Returns:
            List of ensure check dictionaries
        """
        return self.ensure_rules

    def get_prevent_rules(self) -> List[Dict]:
        """
        Get PREVENT rules for LLM-based validation (v2.0 schema).

        Returns:
            List of prevent check dictionaries
        """
        return self.prevent_rules

    def is_llm_based(self) -> bool:
        """
        Check if using LLM-based validation (v2.0) or pattern-based (v1.0).

        Returns:
            True if v2.0 schema is loaded
        """
        return self.schema_version == '2.0'
