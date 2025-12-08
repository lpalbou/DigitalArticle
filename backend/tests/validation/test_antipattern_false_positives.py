"""
Test suite for anti-pattern validation to prevent false positives.

This test suite ensures that legitimate pandas/numpy operations are not
falsely flagged as anti-patterns while still catching actual errors.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.execution_service import ExecutionService


def test_pandas_column_assignment_valid():
    """Test that pandas multi-level column renaming is NOT flagged as anti-pattern."""
    service = ExecutionService()

    # This is VALID pandas code - should NOT trigger anti-pattern
    code = """
import pandas as pd
summary_stats = pd.DataFrame({'A_mean': [1], 'A_std': [2]})
summary_stats.columns = ['_'.join(col).strip() for col in summary_stats.columns]
"""

    is_valid, error_msg, suggestions = service.validate_code_syntax(code)

    assert is_valid, f"Valid pandas code was incorrectly flagged: {error_msg}"
    print("✅ PASS: Pandas column assignment NOT flagged as anti-pattern")


def test_dataframe_attribute_assignment_valid():
    """Test that DataFrame attribute assignments are valid."""
    service = ExecutionService()

    # All of these are VALID pandas operations
    test_cases = [
        "df.columns = ['A', 'B', 'C']",
        "df.index = range(10)",
        "result_stats.columns = [c.lower() for c in result_stats.columns]",
        "summary_stats.index.name = 'Patient ID'",
    ]

    for code_line in test_cases:
        code = f"import pandas as pd\n{code_line}"
        is_valid, error_msg, suggestions = service.validate_code_syntax(code)

        assert is_valid, f"Valid code '{code_line}' was incorrectly flagged: {error_msg}"
        print(f"✅ PASS: '{code_line}' validated correctly")


def test_actual_antipatterns_caught():
    """Test that actual anti-patterns ARE caught."""
    service = ExecutionService()

    # These SHOULD trigger anti-patterns
    bad_cases = [
        ("random.choice=['A', 'B']", "Function call written as assignment"),
        ("np.random=['value']", "Function call written as assignment"),
        ("pd.read_csv=['file.csv']", "Function call written as assignment"),
    ]

    for code_line, expected_error in bad_cases:
        code = f"import random\nimport numpy as np\nimport pandas as pd\n{code_line}"
        is_valid, error_msg, suggestions = service.validate_code_syntax(code)

        assert not is_valid, f"Invalid code '{code_line}' was NOT caught!"
        assert expected_error in error_msg, f"Wrong error for '{code_line}': {error_msg}"
        print(f"✅ PASS: '{code_line}' correctly caught as anti-pattern")


def test_stats_substring_variables():
    """Test that variable names containing 'stats' as substring are valid."""
    service = ExecutionService()

    # Variables containing 'stats' but not being module names
    test_cases = [
        "summary_stats.columns = ['A', 'B']",
        "descriptive_stats.index = range(5)",
        "trial_stats.loc[:, 'mean'] = 0",
        "patient_stats = pd.DataFrame()",
    ]

    for code_line in test_cases:
        code = f"import pandas as pd\n{code_line}"
        is_valid, error_msg, suggestions = service.validate_code_syntax(code)

        assert is_valid, f"Valid code '{code_line}' with 'stats' substring was incorrectly flagged: {error_msg}"
        print(f"✅ PASS: '{code_line}' with 'stats' substring validated correctly")


def test_module_stats_assignment_caught():
    """Test that actual scipy.stats assignments ARE caught."""
    service = ExecutionService()

    # This SHOULD trigger anti-pattern (actual module.function assignment)
    code = """
from scipy import stats
stats.ttest=['a', 'b']  # Wrong - should be stats.ttest_ind(a, b)
"""

    is_valid, error_msg, suggestions = service.validate_code_syntax(code)

    assert not is_valid, f"Invalid scipy.stats assignment was NOT caught!"
    assert "Function call written as assignment" in error_msg
    print(f"✅ PASS: Actual scipy.stats.ttest assignment correctly caught")


def test_list_comprehension_with_builtin():
    """Test that list comprehensions with built-in functions are valid."""
    service = ExecutionService()

    # These are VALID uses of built-in functions in list comprehensions
    test_cases = [
        "values = [int(x) for x in ['1', '2', '3']]",
        "names = [str(i) for i in range(10)]",
        "floats = [float(v) for v in data]",
    ]

    for code_line in test_cases:
        code = code_line  # Use the code_line as code
        is_valid, error_msg, suggestions = service.validate_code_syntax(code)

        assert is_valid, f"Valid list comprehension '{code_line}' was incorrectly flagged: {error_msg}"
        print(f"✅ PASS: '{code_line}' validated correctly")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("Testing Anti-Pattern Validation - False Positive Prevention")
    print("="*80 + "\n")

    # Run all tests
    test_pandas_column_assignment_valid()
    test_dataframe_attribute_assignment_valid()
    test_actual_antipatterns_caught()
    test_stats_substring_variables()
    test_module_stats_assignment_caught()
    test_list_comprehension_with_builtin()

    print("\n" + "="*80)
    print("✅ ALL TESTS PASSED - Anti-pattern validation working correctly!")
    print("="*80)
