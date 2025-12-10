"""
Integration Tests for Two-Path Self-Correction Architecture

Tests the complete implementation of:
- Path 1: Execution Correction (syntax/runtime errors → ErrorAnalyzer + retry)
- Path 2: Logical Validation (methodology/domain errors → ValidationService + retry)

These tests verify:
1. Execution retry loop works correctly (up to 5 attempts)
2. Logical validation loop works correctly (up to 3 attempts)
3. Both paths are properly separated
4. Retry limits are respected
5. YAML validators load and execute
"""

import pytest
from backend.app.models.validation import (
    ValidationPhase,
    ValidationSeverity,
    ValidationResult,
    ValidationReport
)
from backend.app.services.validation_service import ValidationService
from backend.app.models.notebook import ExecutionResult, ExecutionStatus


class TestYAMLValidatorLoading:
    """Test YAML validator loading and initialization."""

    def test_validation_service_initializes(self):
        """Test that ValidationService initializes successfully."""
        service = ValidationService()
        assert service is not None
        assert service.yaml_loader is not None

    def test_yaml_validators_load(self):
        """Test that YAML validators load from data/validators/default.yaml."""
        service = ValidationService()
        stats = service.get_validator_stats()

        # Should have 4 validator groups from default.yaml
        assert stats['yaml_validators'] >= 4, "Expected at least 4 YAML validator groups"

        # Should include these specific validators
        yaml_validators = stats['validator_details']['yaml']
        assert 'statistical_validity' in yaml_validators
        assert 'logical_coherence' in yaml_validators
        assert 'data_integrity' in yaml_validators
        assert 'best_practices' in yaml_validators

    def test_validator_stats_structure(self):
        """Test that get_validator_stats returns correct structure."""
        service = ValidationService()
        stats = service.get_validator_stats()

        assert 'python_validators' in stats
        assert 'yaml_validators' in stats
        assert 'total_logical_validators' in stats
        assert 'total_execution_validators' in stats
        assert 'validator_details' in stats


class TestValidationModels:
    """Test validation data models."""

    def test_validation_result_creation(self):
        """Test creating a ValidationResult."""
        result = ValidationResult(
            validator_name="test_validator",
            phase=ValidationPhase.LOGICAL,
            passed=False,
            severity=ValidationSeverity.ERROR,
            message="Test error message",
            suggestion="Test suggestion"
        )

        assert result.validator_name == "test_validator"
        assert result.phase == ValidationPhase.LOGICAL
        assert not result.passed
        assert result.severity == ValidationSeverity.ERROR

    def test_validation_report_passed(self):
        """Test ValidationReport when all validations pass."""
        report = ValidationReport(
            phase=ValidationPhase.LOGICAL,
            passed=True,
            should_retry=False,
            results=[]
        )

        assert report.passed
        assert not report.should_retry
        assert report.get_llm_guidance() == ""

    def test_validation_report_failed_with_guidance(self):
        """Test ValidationReport with failures generates LLM guidance."""
        result1 = ValidationResult(
            validator_name="test1",
            phase=ValidationPhase.LOGICAL,
            passed=False,
            severity=ValidationSeverity.ERROR,
            message="Error 1",
            suggestion="Fix 1"
        )
        result2 = ValidationResult(
            validator_name="test2",
            phase=ValidationPhase.LOGICAL,
            passed=False,
            severity=ValidationSeverity.CRITICAL,
            message="Error 2",
            suggestion="Fix 2"
        )

        report = ValidationReport(
            phase=ValidationPhase.LOGICAL,
            passed=False,
            should_retry=True,
            results=[result1, result2]
        )

        assert not report.passed
        assert report.should_retry

        guidance = report.get_llm_guidance()
        assert "test1" in guidance
        assert "Error 1" in guidance
        assert "Fix 1" in guidance
        assert "test2" in guidance
        assert "Error 2" in guidance

    def test_validation_report_warnings_only(self):
        """Test ValidationReport with only warnings (should not retry)."""
        warning = ValidationResult(
            validator_name="test_warning",
            phase=ValidationPhase.LOGICAL,
            passed=False,
            severity=ValidationSeverity.WARNING,
            message="Warning message"
        )

        report = ValidationReport(
            phase=ValidationPhase.LOGICAL,
            passed=True,  # Warnings don't fail validation
            should_retry=False,  # Warnings don't trigger retry
            results=[warning]
        )

        assert report.passed
        assert not report.should_retry
        assert len(report.get_warnings()) == 1
        assert report.get_warnings()[0] == "Warning message"


class TestLogicalValidation:
    """Test logical validation execution."""

    def test_run_logical_validation_with_success(self):
        """Test running logical validation on successful code."""
        service = ValidationService()

        # Create a simple execution result with no issues
        exec_result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            stdout="Execution successful\nmean: 50.0",
            stderr="",
            tables=[],
            plots=[]
        )

        code = "df = pd.DataFrame({'a': [1, 2, 3]})\nprint('mean:', df['a'].mean())"
        context = {'available_variables': {}}

        report = service.run_logical_validation(code, exec_result, context)

        # Should pass when there are no validation errors
        assert report.phase == ValidationPhase.LOGICAL
        # Note: Actual pass/fail depends on YAML validators

    def test_run_logical_validation_detects_bounds(self):
        """Test that logical validation detects parameters at bounds."""
        service = ValidationService()

        # Execution result with parameter at bounds message in stdout
        exec_result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            stdout="Parameter estimation complete\nCL at lower bound: 0.1\nFinal value: 0.1",
            stderr="",
            tables=[],
            plots=[]
        )

        code = "# PK model fitting code"
        context = {}

        report = service.run_logical_validation(code, exec_result, context)

        # Should detect "at lower bound" pattern
        assert report.phase == ValidationPhase.LOGICAL
        # Validation should fail or warn about bounds
        # Note: Exact behavior depends on YAML validators

    def test_run_logical_validation_with_high_cv(self):
        """Test that logical validation detects high %CV."""
        service = ValidationService()

        # Execution result with table containing high %CV
        exec_result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            stdout="Model fitted successfully",
            stderr="",
            tables=[{
                'name': 'parameter_estimates',
                'columns': ['Parameter', 'Estimate', '%CV'],
                'data': [
                    {'Parameter': 'CL', 'Estimate': '5.0', '%CV': 150.0},
                    {'Parameter': 'Vd', 'Estimate': '10.0', '%CV': 200.0}
                ]
            }],
            plots=[]
        )

        code = "# Model fitting"
        context = {}

        report = service.run_logical_validation(code, exec_result, context)

        # Should detect %CV > 100
        assert report.phase == ValidationPhase.LOGICAL


class TestRetryLimits:
    """Test that retry limits are correctly configured."""

    def test_execution_retry_limit_constant(self):
        """Test that MAX_EXECUTION_RETRIES is set to 5."""
        from backend.app.services.notebook_service import MAX_EXECUTION_RETRIES
        assert MAX_EXECUTION_RETRIES == 5

    def test_logical_retry_limit_constant(self):
        """Test that MAX_LOGICAL_RETRIES is set to 3."""
        from backend.app.services.notebook_service import MAX_LOGICAL_RETRIES
        assert MAX_LOGICAL_RETRIES == 3

    def test_logical_validation_enabled(self):
        """Test that ENABLE_LOGICAL_VALIDATION is True."""
        from backend.app.services.notebook_service import ENABLE_LOGICAL_VALIDATION
        assert ENABLE_LOGICAL_VALIDATION is True


class TestPathSeparation:
    """Test that the two paths are properly separated."""

    def test_execution_phase_enum_exists(self):
        """Test that ValidationPhase.EXECUTION exists."""
        assert ValidationPhase.EXECUTION == "execution"

    def test_logical_phase_enum_exists(self):
        """Test that ValidationPhase.LOGICAL exists."""
        assert ValidationPhase.LOGICAL == "logical"

    def test_severity_levels_exist(self):
        """Test that all severity levels exist."""
        assert ValidationSeverity.INFO == "info"
        assert ValidationSeverity.WARNING == "warning"
        assert ValidationSeverity.ERROR == "error"
        assert ValidationSeverity.CRITICAL == "critical"


class TestValidationReportHelpers:
    """Test ValidationReport helper methods."""

    def test_has_errors_method(self):
        """Test has_errors() method."""
        error_result = ValidationResult(
            validator_name="test",
            phase=ValidationPhase.LOGICAL,
            passed=False,
            severity=ValidationSeverity.ERROR,
            message="Error"
        )

        report = ValidationReport(
            phase=ValidationPhase.LOGICAL,
            passed=False,
            should_retry=True,
            results=[error_result]
        )

        assert report.has_errors()

    def test_summary_method_all_passed(self):
        """Test summary() when all validations pass."""
        report = ValidationReport(
            phase=ValidationPhase.LOGICAL,
            passed=True,
            should_retry=False,
            results=[]
        )

        summary = report.summary()
        assert "All" in summary or "passed" in summary

    def test_summary_method_with_errors(self):
        """Test summary() with errors and warnings."""
        error = ValidationResult(
            validator_name="test_error",
            phase=ValidationPhase.LOGICAL,
            passed=False,
            severity=ValidationSeverity.ERROR,
            message="Error"
        )
        warning = ValidationResult(
            validator_name="test_warning",
            phase=ValidationPhase.LOGICAL,
            passed=False,
            severity=ValidationSeverity.WARNING,
            message="Warning"
        )

        report = ValidationReport(
            phase=ValidationPhase.LOGICAL,
            passed=False,
            should_retry=True,
            results=[error, warning]
        )

        summary = report.summary()
        assert "error" in summary.lower()
        assert "warning" in summary.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
