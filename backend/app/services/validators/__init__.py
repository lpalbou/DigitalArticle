"""
Validator Framework for Digital Article

Provides base classes and registry for pluggable validation rules.
Validators can check code and execution results for:
- Technical issues (execution phase): syntax, imports, runtime errors
- Logical issues (logical phase): methodological correctness, domain best practices

Users can define custom validators by:
1. Creating YAML files in data/validators/
2. Following the schema defined in default.yaml
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import logging

from ...models.validation import (
    ValidationResult,
    ValidationPhase,
    ValidationSeverity
)

logger = logging.getLogger(__name__)


class BaseValidator(ABC):
    """
    Base class for all validators.

    Validators examine code and execution results to detect issues that should
    trigger retry logic. Each validator focuses on one specific type of check.

    Subclasses must implement validate() to perform their specific check.
    """

    # Metadata - override in subclasses
    name: str = "base_validator"
    phase: ValidationPhase = ValidationPhase.EXECUTION
    description: str = "Base validator (override in subclass)"

    @abstractmethod
    def validate(
        self,
        code: str,
        execution_result: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Optional[ValidationResult]:
        """
        Run validation check on code and execution results.

        Args:
            code: The Python code that was (or will be) executed
            execution_result: Results from code execution (status, stdout, stderr, tables, plots)
                Expected keys: status, stdout, stderr, tables, plots, error_message, traceback
            context: Additional context (available variables, previous cells, etc.)
                Expected keys: available_variables, previous_cells, notebook_id, cell_id

        Returns:
            ValidationResult if check failed, None if check passed
        """
        pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name}, phase={self.phase})>"


class ValidatorRegistry:
    """
    Registry for validators - allows user-defined validators.

    This class maintains separate lists of validators for each phase
    (execution vs logical) and provides methods to register and retrieve them.

    Validators can be registered via:
    1. Decorator: @ValidatorRegistry.register
    2. YAML files: Automatically loaded from data/validators/
    """

    # Class-level storage for registered validators
    _execution_validators: List[type[BaseValidator]] = []
    _logical_validators: List[type[BaseValidator]] = []

    @classmethod
    def register(cls, validator_class: type[BaseValidator]) -> type[BaseValidator]:
        """
        Decorator to register a validator class.

        Example:
            @ValidatorRegistry.register
            class MyValidator(BaseValidator):
                name = "my_validator"
                phase = ValidationPhase.LOGICAL
                ...

        Args:
            validator_class: The validator class to register

        Returns:
            The same validator class (for decorator chaining)
        """
        if not issubclass(validator_class, BaseValidator):
            raise TypeError(f"{validator_class} must inherit from BaseValidator")

        # Instantiate to get phase (since it might be an instance variable)
        try:
            instance = validator_class()
            phase = instance.phase
        except Exception as e:
            logger.warning(f"Could not instantiate {validator_class.__name__} for registration: {e}")
            # Fallback to class attribute
            phase = getattr(validator_class, 'phase', ValidationPhase.EXECUTION)

        # Add to appropriate list
        if phase == ValidationPhase.EXECUTION:
            cls._execution_validators.append(validator_class)
            logger.info(f"Registered execution validator: {validator_class.__name__}")
        else:
            cls._logical_validators.append(validator_class)
            logger.info(f"Registered logical validator: {validator_class.__name__}")

        return validator_class

    @classmethod
    def get_execution_validators(cls) -> List[BaseValidator]:
        """
        Get all registered execution validators.

        Returns:
            List of instantiated execution validator objects
        """
        return [validator_cls() for validator_cls in cls._execution_validators]

    @classmethod
    def get_logical_validators(cls) -> List[BaseValidator]:
        """
        Get all registered logical validators.

        Returns:
            List of instantiated logical validator objects
        """
        return [validator_cls() for validator_cls in cls._logical_validators]

    @classmethod
    def clear(cls) -> None:
        """Clear all registered validators (useful for testing)."""
        cls._execution_validators.clear()
        cls._logical_validators.clear()
        logger.info("Cleared all registered validators")

    @classmethod
    def count(cls) -> Dict[str, int]:
        """
        Get count of registered validators by phase.

        Returns:
            Dict with counts: {"execution": int, "logical": int}
        """
        return {
            "execution": len(cls._execution_validators),
            "logical": len(cls._logical_validators)
        }

    @classmethod
    def list_validators(cls) -> Dict[str, List[str]]:
        """
        List all registered validators by phase.

        Returns:
            Dict with validator names by phase
        """
        return {
            "execution": [v.__name__ for v in cls._execution_validators],
            "logical": [v.__name__ for v in cls._logical_validators]
        }


# Example validator for testing/documentation
class ExampleValidator(BaseValidator):
    """
    Example validator showing the basic structure.

    This validator does nothing and always passes - it's just for documentation.
    """

    name = "example_validator"
    phase = ValidationPhase.LOGICAL
    description = "Example validator (does nothing)"

    def validate(
        self,
        code: str,
        execution_result: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Optional[ValidationResult]:
        """Always passes - this is just an example."""
        # Example check (always passes)
        if "definitely_invalid_code" in code:
            return ValidationResult(
                validator_name=self.name,
                phase=self.phase,
                passed=False,
                severity=ValidationSeverity.ERROR,
                message="Found invalid code pattern",
                suggestion="Remove the invalid pattern"
            )

        return None  # None means validation passed


# Don't register the example validator by default
# Uncomment below to include it in the registry:
# ValidatorRegistry.register(ExampleValidator)
