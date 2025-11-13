"""
Tests for code syntax validation in ExecutionService.

These tests verify that the pre-execution validation catches common syntax errors
and anti-patterns BEFORE execution, providing helpful feedback to the LLM.
"""

import pytest
from backend.app.services.execution_service import ExecutionService


@pytest.fixture
def execution_service():
    """Create an execution service instance for testing."""
    return ExecutionService()


def test_valid_code_passes_validation(execution_service):
    """Test that valid Python code passes validation."""
    valid_code = """
import pandas as pd
import random

data = [1, 2, 3, 4, 5]
choice = random.choice(data)
print(choice)
"""
    is_valid, error_msg, suggestions = execution_service.validate_code_syntax(valid_code)

    assert is_valid is True
    assert error_msg is None
    assert suggestions is None


def test_random_choice_with_equals_fails_validation(execution_service):
    """Test that random.choice= syntax error is caught."""
    # This is the EXACT error from the user's logs
    invalid_code = """
import random

outcome = random.choice=['RECOVERED', 'RECOVERING', 'NOT RECOVERED']
"""
    is_valid, error_msg, suggestions = execution_service.validate_code_syntax(invalid_code)

    assert is_valid is False
    assert error_msg is not None
    assert suggestions is not None
    assert any('=' in s and 'instead of' in s for s in suggestions)


def test_function_call_with_equals_fails_validation(execution_service):
    """Test that np.random.normal= syntax error is caught."""
    invalid_code = """
import numpy as np

value = np.random.normal=0, 1
"""
    is_valid, error_msg, suggestions = execution_service.validate_code_syntax(invalid_code)

    assert is_valid is False
    assert error_msg is not None
    assert suggestions is not None


def test_function_call_with_brackets_fails_validation(execution_service):
    """Test that random.choice[] syntax error is caught."""
    invalid_code = """
import random

items = ['A', 'B', 'C']
choice = random.choice[items]
"""
    is_valid, error_msg, suggestions = execution_service.validate_code_syntax(invalid_code)

    assert is_valid is False
    assert error_msg is not None
    assert suggestions is not None
    assert any('brackets' in s.lower() for s in suggestions)


def test_missing_parentheses_fails_validation(execution_service):
    """Test that syntax errors from missing parentheses are caught."""
    invalid_code = """
import random

# Missing closing parenthesis
data = random.choice(['A', 'B', 'C'
print(data)
"""
    is_valid, error_msg, suggestions = execution_service.validate_code_syntax(invalid_code)

    assert is_valid is False
    assert 'Syntax Error' in error_msg


def test_anti_pattern_function_assignment(execution_service):
    """Test that assigning to library functions is caught."""
    invalid_code = """
import random

# This would overwrite the random.choice function
random.choice = ['MILD', 'MODERATE', 'SEVERE']
"""
    is_valid, error_msg, suggestions = execution_service.validate_code_syntax(invalid_code)

    # This specific pattern should be caught by the anti-pattern detector
    assert is_valid is False
    assert 'Anti-pattern' in error_msg or 'Syntax Error' in error_msg
    assert suggestions is not None


def test_valid_list_comprehension_passes(execution_service):
    """Test that valid list comprehensions pass validation."""
    valid_code = """
import random

data = [random.choice(['A', 'B', 'C']) for _ in range(10)]
print(data)
"""
    is_valid, error_msg, suggestions = execution_service.validate_code_syntax(valid_code)

    assert is_valid is True
    assert error_msg is None


def test_validation_provides_helpful_suggestions(execution_service):
    """Test that validation provides actionable suggestions."""
    invalid_code = """
import random
outcome = random.choice=['RECOVERED', 'RECOVERING']
"""
    is_valid, error_msg, suggestions = execution_service.validate_code_syntax(invalid_code)

    assert is_valid is False
    assert suggestions is not None
    # Should mention CORRECT and WRONG examples
    suggestion_text = ' '.join(suggestions)
    assert 'CORRECT' in suggestion_text or 'RIGHT' in suggestion_text
    assert 'WRONG' in suggestion_text or 'instead' in suggestion_text.lower()


def test_complex_code_with_multiple_functions(execution_service):
    """Test validation on more complex code with multiple function calls."""
    valid_code = """
import pandas as pd
import numpy as np
import random

# Multiple valid function calls
data = np.random.randn(100)
choices = [random.choice(['A', 'B']) for _ in range(10)]
df = pd.DataFrame({'values': data[:10], 'categories': choices})
mean_val = df['values'].mean()
print(mean_val)
"""
    is_valid, error_msg, suggestions = execution_service.validate_code_syntax(valid_code)

    assert is_valid is True
    assert error_msg is None


def test_invalid_type_conversion_syntax(execution_service):
    """Test that invalid type conversion syntax is caught."""
    invalid_code = """
value = "123"
# Using brackets instead of parentheses
number = int[value]
"""
    is_valid, error_msg, suggestions = execution_service.validate_code_syntax(invalid_code)

    assert is_valid is False
    assert error_msg is not None
