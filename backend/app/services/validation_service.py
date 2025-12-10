"""
Validation Service for Digital Article

Orchestrates validation across both phases:
1. Execution Validation (technical): Code runs without Python errors
2. Logical Validation (semantic): Code produces valid/meaningful results

This service coordinates:
- Python-based validators (via ValidatorRegistry)
- YAML-based validators (via YAMLValidatorLoader)
- Aggregation of results into ValidationReport
"""

import logging
from typing import Dict, Any, List, Tuple, Optional

from ..models.notebook import ExecutionResult
from ..models.validation import (
    ValidationReport,
    ValidationResult,
    ValidationPhase,
    ValidationSeverity
)
from .validators import ValidatorRegistry
from .validators.yaml_loader import YAMLValidatorLoader
from .llm_validation_service import LLMValidationService

logger = logging.getLogger(__name__)


class ValidationService:
    """
    Orchestrates validation across both execution and logical phases.

    This service runs all registered validators (both Python and YAML-based)
    and aggregates their results into structured ValidationReport objects.
    """

    def __init__(self, llm_service=None):
        """
        Initialize validation service with YAML loader and optional LLM service.

        Args:
            llm_service: LLMService instance for LLM-based validation (v2.0 schema)
        """
        # Load YAML validators from data/validators/
        try:
            self.yaml_loader = YAMLValidatorLoader()
            logger.info(f"Initialized ValidationService with YAML validators")
        except Exception as e:
            logger.error(f"Failed to initialize YAML validators: {e}")
            logger.warning("ValidationService will operate without YAML validators")
            self.yaml_loader = None

        # Initialize LLM validator if LLM service provided
        self.llm_service = llm_service
        if llm_service and self.yaml_loader and self.yaml_loader.is_llm_based():
            self.llm_validator = LLMValidationService(llm_service)
            logger.info("✅ LLM-based validation enabled (v2.0 schema detected)")
        else:
            self.llm_validator = None
            if self.yaml_loader and not self.yaml_loader.is_llm_based():
                logger.info("ℹ️ Using pattern-based validation (v1.0 schema)")

    def run_execution_validation(
        self,
        code: str,
        execution_result: ExecutionResult,
        context: Dict[str, Any]
    ) -> ValidationReport:
        """
        Run all execution validators (currently not used - execution errors
        are handled by the existing ErrorAnalyzer + retry loop).

        This method is here for future extensibility if we want to add
        pre-execution validation rules.

        Args:
            code: Python code to validate
            execution_result: Results from execution
            context: Additional context

        Returns:
            ValidationReport for execution phase
        """
        results = []

        # Get Python-based execution validators
        for validator in ValidatorRegistry.get_execution_validators():
            try:
                result = validator.validate(
                    code,
                    self._execution_result_to_dict(execution_result),
                    context
                )
                if result:
                    results.append(result)
            except Exception as e:
                logger.warning(f"Execution validator {validator.name} failed: {e}")

        # Determine overall status
        has_errors = any(
            not r.passed and r.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL)
            for r in results
        )

        return ValidationReport(
            phase=ValidationPhase.EXECUTION,
            passed=not has_errors,
            should_retry=has_errors,
            results=results
        )

    def run_logical_validation(
        self,
        code: str,
        execution_result: ExecutionResult,
        context: Dict[str, Any]
    ) -> Tuple[ValidationReport, Optional[str], Optional[Dict]]:
        """
        Run all logical validators after successful code execution.

        This is the main validation phase that catches methodological issues,
        statistical problems, and domain violations AFTER code runs successfully.

        Args:
            code: Python code that was executed
            execution_result: Results from execution (must be SUCCESS status)
            context: Additional context (available variables, previous cells, etc.)

        Returns:
            Tuple of (ValidationReport, trace_id, full_trace)
        """
        results = []

        # Store trace data for return (will be populated if LLM validation runs)
        llm_trace_id = None
        llm_full_trace = None

        # Convert ExecutionResult to dict for validators
        exec_result_dict = self._execution_result_to_dict(execution_result)

        # 1. Run Python-based logical validators
        for validator in ValidatorRegistry.get_logical_validators():
            try:
                result = validator.validate(code, exec_result_dict, context)
                if result:
                    results.append(result)
                    logger.info(
                        f"Validator {validator.name}: {'❌ FAILED' if not result.passed else '✅ PASSED'}"
                    )
            except Exception as e:
                logger.warning(f"Logical validator {validator.name} failed with exception: {e}")
                # Don't let validator failures break the validation process

        # 2. Run YAML-based validators (LLM or pattern-based)
        if self.llm_validator:
            # Use LLM-based semantic validation (v2.0 schema)
            try:
                ensure_rules = self.yaml_loader.get_ensure_rules()
                prevent_rules = self.yaml_loader.get_prevent_rules()

                logger.info(f"🤖 Running LLM validation with {len(ensure_rules)} ENSURE + {len(prevent_rules)} PREVENT rules")

                # Store trace data
                llm_results, llm_trace_id, llm_full_trace = self.llm_validator.validate(
                    code, exec_result_dict, context, ensure_rules, prevent_rules
                )

                results.extend(llm_results)
                if llm_results:
                    logger.info(f"LLM validation produced {len(llm_results)} finding(s)")

            except Exception as e:
                logger.error(f"LLM validation failed: {e}", exc_info=True)

        elif self.yaml_loader:
            # Use pattern-based validation (v1.0 schema)
            try:
                yaml_results = self.yaml_loader.validate(code, exec_result_dict, context)
                results.extend(yaml_results)
                if yaml_results:
                    logger.info(f"Pattern-based validators produced {len(yaml_results)} finding(s)")
            except Exception as e:
                logger.error(f"Pattern-based validation failed: {e}")

        # 3. Aggregate results
        has_errors = any(
            not r.passed and r.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL)
            for r in results
        )

        report = ValidationReport(
            phase=ValidationPhase.LOGICAL,
            passed=not has_errors,
            should_retry=has_errors,
            results=results
        )

        # Log summary
        if results:
            logger.info(f"📊 Logical Validation Summary: {report.summary()}")
            if has_errors:
                logger.warning(f"🔁 Retry recommended due to {sum(1 for r in results if not r.passed)} validation failure(s)")
        else:
            logger.info("✅ All logical validations passed (no findings)")

        # BUG FIX 1: Return trace data along with report
        return report, llm_trace_id, llm_full_trace

    def _execution_result_to_dict(self, execution_result: ExecutionResult) -> Dict[str, Any]:
        """
        Convert ExecutionResult to dictionary for validators.

        Args:
            execution_result: Pydantic ExecutionResult model

        Returns:
            Dictionary with execution result data
        """
        return {
            'status': execution_result.status,
            'stdout': execution_result.stdout,
            'stderr': execution_result.stderr,
            'tables': execution_result.tables,
            'plots': execution_result.plots,
            'interactive_plots': execution_result.interactive_plots,
            'error_message': execution_result.error_message,
            'error_type': execution_result.error_type,
            'traceback': execution_result.traceback,
            'warnings': execution_result.warnings,
            'execution_time': execution_result.execution_time
        }

    def reload_yaml_validators(self) -> None:
        """
        Reload YAML validators from disk.

        Useful during development when validator files are being modified.
        """
        if self.yaml_loader:
            self.yaml_loader.reload()
            logger.info("Reloaded YAML validators")
        else:
            logger.warning("No YAML loader to reload")

    def get_validator_stats(self) -> Dict[str, Any]:
        """
        Get statistics about registered validators.

        Returns:
            Dict with validator counts and names
        """
        python_stats = ValidatorRegistry.count()

        # BUG FIX 2: Handle both v1.0 (rules) and v2.0 (ensure_rules + prevent_rules)
        if self.yaml_loader:
            if self.yaml_loader.is_llm_based():
                # v2.0: Count ensure + prevent rules
                ensure_count = len(self.yaml_loader.ensure_rules)
                prevent_count = len(self.yaml_loader.prevent_rules)
                yaml_count = ensure_count + prevent_count
                yaml_names = (
                    [f"ensure:{r['name']}" for r in self.yaml_loader.ensure_rules] +
                    [f"prevent:{r['name']}" for r in self.yaml_loader.prevent_rules]
                )
            else:
                # v1.0: Count pattern-based rules
                yaml_count = len(self.yaml_loader.rules)
                yaml_names = list(self.yaml_loader.rules.keys())
        else:
            yaml_count = 0
            yaml_names = []

        return {
            'python_validators': python_stats,
            'yaml_validators': yaml_count,
            'total_logical_validators': python_stats['logical'] + yaml_count,
            'total_execution_validators': python_stats['execution'],
            'schema_version': self.yaml_loader.schema_version if self.yaml_loader else '1.0',
            'validator_details': {
                'python': ValidatorRegistry.list_validators(),
                'yaml': yaml_names
            }
        }
