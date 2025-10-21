"""
Tests for numpy type conversion error analysis.

These tests verify that the ErrorAnalyzer correctly identifies and provides
helpful guidance for numpy type conversion errors.
"""

import pytest
import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.services.error_analyzer import ErrorAnalyzer, ErrorContext


class TestNumpyTimedeltaErrors:
    """Test numpy timedelta type conversion error analysis."""

    def test_timedelta_numpy_int64_detection(self):
        """Test detection of the exact error from user's issue."""
        analyzer = ErrorAnalyzer()

        error_message = "unsupported type for timedelta days component: numpy.int64"
        error_type = "TypeError"
        traceback = """
Traceback (most recent call last):
  File "<string>", line 21, in <module>
TypeError: unsupported type for timedelta days component: numpy.int64
"""
        code = "td = timedelta(days=np.random.randint(1, 30))"

        context = analyzer.analyze_error(error_message, error_type, traceback, code)

        assert isinstance(context, ErrorContext)
        assert context.error_type == "TypeError"
        assert "timedelta" in context.enhanced_message.lower()
        assert "numpy" in context.enhanced_message.lower()

        # Check that suggestions include conversion strategies
        suggestions_text = "\n".join(context.suggestions)
        assert "int(" in suggestions_text or ".item()" in suggestions_text
        assert "safe_timedelta" in suggestions_text
        assert "pd.to_timedelta" in suggestions_text

    def test_timedelta_error_provides_multiple_solutions(self):
        """Test that multiple fix strategies are provided."""
        analyzer = ErrorAnalyzer()

        error_message = "unsupported type for timedelta days component: numpy.int64"
        error_type = "TypeError"

        context = analyzer.analyze_error(error_message, error_type, "", "")

        suggestions_text = "\n".join(context.suggestions)

        # Should provide at least 3 methods
        assert "METHOD 1" in suggestions_text
        assert "METHOD 2" in suggestions_text
        assert "METHOD 3" in suggestions_text or "COMMON SCENARIOS" in suggestions_text

    def test_timedelta_error_shows_wrong_and_right_patterns(self):
        """Test that both wrong and correct patterns are shown."""
        analyzer = ErrorAnalyzer()

        error_message = "unsupported type for timedelta days component: numpy.int64"
        error_type = "TypeError"

        context = analyzer.analyze_error(error_message, error_type, "", "")

        suggestions_text = "\n".join(context.suggestions)

        # Should show both wrong and right patterns
        assert "WRONG" in suggestions_text or "wrong" in suggestions_text.lower()
        assert "RIGHT" in suggestions_text or "right" in suggestions_text.lower()


class TestGeneralNumpyTypeErrors:
    """Test general numpy type conversion error analysis."""

    def test_numpy_type_conversion_detection(self):
        """Test detection of general numpy type conversion errors."""
        analyzer = ErrorAnalyzer()

        error_message = "unsupported type: expected int, got numpy.int64"
        error_type = "TypeError"
        traceback = "TypeError: unsupported type: expected int, got numpy.int64"
        code = "range(np_value)"

        context = analyzer.analyze_error(error_message, error_type, traceback, code)

        assert "numpy" in context.enhanced_message.lower()
        suggestions_text = "\n".join(context.suggestions)
        assert "convert" in suggestions_text.lower()


class TestTypeConversionHelpers:
    """Test the type conversion helper functions."""

    def test_safe_timedelta_helper(self):
        """Test safe_timedelta helper function."""
        import numpy as np
        from datetime import timedelta

        # Create the helper function (same as in execution_service.py)
        def safe_timedelta(**kwargs):
            converted_kwargs = {}
            for key, value in kwargs.items():
                if hasattr(value, 'item'):
                    converted_kwargs[key] = value.item()
                elif isinstance(value, (np.integer, np.floating)):
                    converted_kwargs[key] = value.item()
                else:
                    converted_kwargs[key] = value
            return timedelta(**converted_kwargs)

        # Test with numpy types
        np_int = np.int64(5)
        td = safe_timedelta(days=np_int)
        assert td.days == 5

        # Test with Python types (should still work)
        td = safe_timedelta(days=3, hours=2)
        assert td.days == 3

    def test_to_python_type_helper(self):
        """Test to_python_type helper function."""
        import numpy as np
        import pandas as pd

        def to_python_type(value):
            # Check array types first before hasattr('item')
            if isinstance(value, np.ndarray):
                return value.tolist()
            elif isinstance(value, pd.Series):
                return value.tolist()
            elif hasattr(value, 'item') and not isinstance(value, (np.ndarray, pd.Series)):
                return value.item()
            elif isinstance(value, (np.integer, np.floating, np.bool_)):
                return value.item()
            else:
                return value

        # Test numpy scalar
        np_int = np.int64(42)
        assert to_python_type(np_int) == 42
        assert type(to_python_type(np_int)) == int

        # Test numpy array
        np_arr = np.array([1, 2, 3])
        result = to_python_type(np_arr)
        assert result == [1, 2, 3]
        assert type(result) == list

        # Test pandas Series
        series = pd.Series([1, 2, 3])
        result = to_python_type(series)
        assert len(result) == 3
        assert type(result) == list

    def test_safe_int_helper(self):
        """Test safe_int helper function."""
        import numpy as np

        def safe_int(value):
            if hasattr(value, 'item'):
                return int(value.item())
            return int(value)

        # Test with numpy type
        np_int = np.int64(42)
        result = safe_int(np_int)
        assert result == 42
        assert type(result) == int

        # Test with Python type
        result = safe_int(42)
        assert result == 42


class TestRealTimedeltaScenario:
    """Test the real timedelta scenario from user's error."""

    def test_real_error_enhancement(self):
        """
        Test enhancement of the exact error the user encountered.

        This demonstrates the comprehensive guidance provided for this specific error.
        """
        analyzer = ErrorAnalyzer()

        # The exact error from the user's issue
        error_message = "unsupported type for timedelta days component: numpy.int64"
        error_type = "TypeError"
        traceback = """Traceback (most recent call last):
  File "<string>", line 21, in <module>
TypeError: unsupported type for timedelta days component: numpy.int64"""

        # Simulated code that might have caused this
        code = """
# Generate SDTM dataset with random dates
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

num_patients = 100
base_date = datetime(2023, 1, 1)

# Generate enrollment dates
enrollment_days = np.random.randint(0, 365, num_patients)  # numpy.int64 array
enrollment_dates = [base_date + timedelta(days=days) for days in enrollment_days]  # FAILS HERE
"""

        context = analyzer.analyze_error(error_message, error_type, traceback, code)

        # Verify comprehensive guidance
        assert context is not None
        formatted = analyzer.format_for_llm(context)

        print("\n" + "=" * 80)
        print("ENHANCED ERROR CONTEXT FOR TIMEDELTA NUMPY TYPE ERROR:")
        print("=" * 80)
        print(formatted)
        print("=" * 80)

        # Verify key elements
        assert "timedelta" in formatted.lower()
        assert "numpy" in formatted.lower()
        assert "convert" in formatted.lower()
        assert "int(" in formatted or ".item()" in formatted
        assert "safe_timedelta" in formatted
        assert "pd.to_timedelta" in formatted

        # Should explain the root cause
        assert "python" in formatted.lower() and "type" in formatted.lower()

    def test_comparison_before_after(self):
        """Compare raw error vs enhanced error for timedelta issue."""
        analyzer = ErrorAnalyzer()

        error_message = "unsupported type for timedelta days component: numpy.int64"
        error_type = "TypeError"
        traceback = "TypeError: unsupported type for timedelta days component: numpy.int64"

        context = analyzer.analyze_error(error_message, error_type, traceback, "")
        enhanced = analyzer.format_for_llm(context)

        raw_length = len(error_message + traceback)
        enhanced_length = len(enhanced)

        # Enhanced should be significantly more detailed
        assert enhanced_length > raw_length * 5

        print("\n" + "=" * 80)
        print(f"RAW ERROR: {raw_length} characters")
        print(f"ENHANCED: {enhanced_length} characters")
        print(f"IMPROVEMENT: {enhanced_length / raw_length:.1f}x more detailed")
        print("=" * 80)


class TestErrorAnalyzerRobustness:
    """Test robustness of numpy error analyzers."""

    def test_handles_partial_information(self):
        """Test that analyzer works with minimal information."""
        analyzer = ErrorAnalyzer()

        context = analyzer.analyze_error(
            error_message="unsupported type for timedelta",
            error_type="TypeError",
            traceback="",
            code=""
        )

        # Should still provide helpful context
        assert context is not None
        assert len(context.suggestions) > 0

    def test_distinguishes_timedelta_from_other_type_errors(self):
        """Test that timedelta errors are distinguished from generic TypeError."""
        analyzer = ErrorAnalyzer()

        # Timedelta-specific error
        timedelta_context = analyzer.analyze_error(
            error_message="unsupported type for timedelta days component: numpy.int64",
            error_type="TypeError",
            traceback="",
            code=""
        )

        # Generic TypeError
        generic_context = analyzer.analyze_error(
            error_message="'str' object cannot be interpreted as an integer",
            error_type="TypeError",
            traceback="",
            code=""
        )

        # Timedelta should have specific guidance
        timedelta_text = "\n".join(timedelta_context.suggestions).lower()
        assert "timedelta" in timedelta_text

        # Generic should not mention timedelta
        generic_text = "\n".join(generic_context.suggestions).lower()
        assert "timedelta" not in generic_text


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
